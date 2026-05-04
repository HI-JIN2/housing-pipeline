#!/bin/bash

# 종료 시그널 핸들러 (Ctrl+C를 누르면 켜진 서비스들이 함께 꺼지도록 훅을 설정합니다)
cleanup() {
    echo ""
    echo "======================================"
    echo "🛑 프로세스 종료 시그널이 감지되었습니다."
    echo "======================================"
    echo "1/2 끄는 중... [FastAPI & React 에이전트 서버들]"
    kill $PARSER_PID 2>/dev/null
    kill $ADMIN_PID 2>/dev/null
    kill $GEO_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "uvicorn main:app" 2>/dev/null
    lsof -i :8000 -t | xargs kill -9 2>/dev/null
    lsof -i :8002 -t | xargs kill -9 2>/dev/null
    lsof -i :8001 -t | xargs kill -9 2>/dev/null
    lsof -i :5173 -t | xargs kill -9 2>/dev/null
    
    echo "2/2 끄는 중... [Docker-Compose 인프라]"
    if [ "${DOCKER_STARTED_BY_SCRIPT}" = "1" ]; then
        docker compose stop mongodb db >/dev/null 2>&1 || true
    else
        echo "    -> Docker 컨테이너는 유지합니다 (스크립트에서 시작하지 않음)"
    fi
    
    echo "모든 서비스가 안전하게 종료되었습니다. 바이바이! 👋"
    exit 0
}

# Trap 인터럽트 세팅
trap cleanup SIGINT SIGTERM

echo "======================================"
echo "🚀 공고zip All-in-one 로컬 실행 스크립트"
echo "======================================"

echo "🧹 이전 좀비 프로세스 정리 중..."
lsof -i :8000 -t | xargs kill -9 > /dev/null 2>&1 || true
lsof -i :8002 -t | xargs kill -9 > /dev/null 2>&1 || true
lsof -i :8001 -t | xargs kill -9 > /dev/null 2>&1 || true
lsof -i :5173 -t | xargs kill -9 > /dev/null 2>&1 || true

echo "[1/4] Docker Compose 인프라 (MongoDB, PostGIS) 시작 중..."

if [ "${SKIP_DOCKER}" = "1" ]; then
    echo "    -> SKIP_DOCKER=1: Docker 제어를 건너뜁니다."
    if ! (nc -z 127.0.0.1 27017 >/dev/null 2>&1 && nc -z 127.0.0.1 5433 >/dev/null 2>&1); then
        echo "❌ MongoDB(27017) 또는 Postgres(5433)가 열려있지 않습니다."
        echo "   - Docker Desktop에서 mongodb/db를 먼저 실행한 뒤 다시 시도해주세요."
        exit 1
    fi
    DOCKER_STARTED_BY_SCRIPT=0
else
for i in {1..30}; do
    if docker info >/dev/null 2>&1; then
        break
    fi
    echo "    -> Docker 엔진 대기 중... (${i}/30)"
    sleep 2
done

if ! docker info >/dev/null 2>&1; then
    # Sometimes Docker Desktop UI is flaky but the DB ports are already mapped.
    if nc -z 127.0.0.1 27017 >/dev/null 2>&1 && nc -z 127.0.0.1 5433 >/dev/null 2>&1; then
        echo "⚠️ Docker 엔진 API 연결은 실패했지만, DB 포트는 열려있습니다. Docker 제어 없이 계속 진행합니다."
        DOCKER_STARTED_BY_SCRIPT=0
    else
        echo "❌ Docker 엔진에 연결할 수 없습니다. Docker Desktop이 완전히 실행(Engine running)된 뒤 다시 시도해주세요."
        echo "   - Docker Desktop에서 Troubleshoot -> Restart 권장"
        echo "   - 디스크 용량이 부족하면(특히 /System/Volumes/Data 90%+) Docker가 자주 멈춥니다."
        exit 1
    fi
fi

# If DB ports are already open, avoid touching Docker Desktop (more stable).
if nc -z 127.0.0.1 27017 >/dev/null 2>&1 && nc -z 127.0.0.1 5433 >/dev/null 2>&1; then
    echo "    -> MongoDB/Postgres가 이미 실행 중입니다. Docker compose는 실행하지 않습니다."
    DOCKER_STARTED_BY_SCRIPT=0
else
    DOCKER_STARTED_BY_SCRIPT=1
    docker compose up -d mongodb db || {
        echo "❌ docker compose 실행 실패: Docker 엔진 상태를 확인해주세요."
        exit 1
    }

    echo "    -> MongoDB 포트(27017) 대기 중..."
    for i in {1..30}; do
        nc -z 127.0.0.1 27017 >/dev/null 2>&1 && break
        sleep 1
    done

    echo "    -> Postgres 포트(5433) 대기 중..."
    for i in {1..30}; do
        nc -z 127.0.0.1 5433 >/dev/null 2>&1 && break
        sleep 1
    done
fi
fi

echo "[2/5] Parser Agent (사용자 조회 API) 포트 8000 실행 중..."
cd parser-agent
if [ "${SKIP_INSTALL}" = "1" ]; then
    echo "    -> SKIP_INSTALL=1: pip 설치를 건너뜁니다."
else
    pip3 install -r requirements.txt > /dev/null 2>&1
fi
python3 -m uvicorn main:app --reload --port 8000 &
PARSER_PID=$!
cd ..

echo "[3/5] Admin Agent (업로드 및 관리 API) 포트 8002 실행 중..."
cd admin-agent
if [ "${SKIP_INSTALL}" = "1" ]; then
    echo "    -> SKIP_INSTALL=1: pip 설치를 건너뜁니다."
else
    pip3 install -r requirements.txt > /dev/null 2>&1
fi
python3 -m uvicorn main:app --reload --port 8002 &
ADMIN_PID=$!
cd ..

echo "[4/5] Geo Agent (위치 정보/길찾기) 포트 8001 실행 중..."
cd geo-agent
if [ "${SKIP_INSTALL}" = "1" ]; then
    echo "    -> SKIP_INSTALL=1: pip 설치를 건너뜁니다."
else
    pip3 install -r requirements.txt > /dev/null 2>&1
fi
echo "    -> 파싱된 역 좌표 정보를 바탕으로 DB를 초기화합니다..."
python3 scripts/load_stations.py "data/stations.csv" || true
python3 -m uvicorn main:app --reload --port 8001 &
GEO_PID=$!
cd ..

echo "[5/5] Frontend (React) 포트 5173 실행 중..."
cd frontend
if [ "${SKIP_INSTALL}" = "1" ]; then
    echo "    -> SKIP_INSTALL=1: npm 설치를 건너뜁니다."
else
    if [ ! -d "node_modules" ]; then
        npm install > /dev/null 2>&1
    fi
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo " "
echo "✅ 모든 서비스가 성공적으로 구동되었습니다!"
echo "👉 웹 브라우저를 열고 http://localhost:5173 에 접속하세요. (신규 React 대시보드)"
echo "   (종료하시려면 'Ctrl + C'를 누르시면 됩니다)"
echo "--------------------------------------"
echo "👇 아래부터는 각 서비스의 실시간 통합 로그가 출력됩니다."

# 무한 대기 (백그라운드로 띄워진 앱들의 로그가 터미널에 섞여서 나오게 함)
wait
