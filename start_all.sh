#!/bin/bash

# 종료 시그널 핸들러 (Ctrl+C를 누르면 켜진 서비스들이 함께 꺼지도록 훅을 설정합니다)
cleanup() {
    echo ""
    echo "======================================"
    echo "🛑 프로세스 종료 시그널이 감지되었습니다."
    echo "======================================"
    echo "1/2 끄는 중... [FastAPI 에이전트 서버들]"
    kill $PARSER_PID 2>/dev/null
    kill $GEO_PID 2>/dev/null
    pkill -f "uvicorn main:app" 2>/dev/null
    lsof -i :8000 -t | xargs kill -9 2>/dev/null
    lsof -i :8001 -t | xargs kill -9 2>/dev/null
    
    echo "2/2 끄는 중... [Docker-Compose 인프라]"
    docker-compose stop
    
    echo "모든 서비스가 안전하게 종료되었습니다. 바이바이! 👋"
    exit 0
}

# Trap 인터럽트 세팅
trap cleanup SIGINT SIGTERM

echo "======================================"
echo "🚀 Housing Pipeline 전체 구동 스크립트"
echo "======================================"

echo "🧹 이전 좀비 프로세스 정리 중..."
lsof -i :8000 -t | xargs kill -9 > /dev/null 2>&1 || true
lsof -i :8001 -t | xargs kill -9 > /dev/null 2>&1 || true

echo "[1/3] Docker Compose 인프라 (Kafka, PostGIS) 시작 중..."
docker-compose up -d

echo "[2/3] Parser Agent (업로드 UI 및 파서) 포트 8000 실행 중..."
cd parser-agent
pip3 install -r requirements.txt > /dev/null 2>&1
python3 -m uvicorn main:app --reload --port 8000 &
PARSER_PID=$!
cd ..

echo "[3/3] Geo Agent (위치 정보/길찾기) 포트 8001 실행 중..."
cd geo-agent
pip3 install -r requirements.txt > /dev/null 2>&1
echo "    -> 파싱된 역 좌표 정보를 바탕으로 DB를 초기화합니다..."
python3 scripts/load_stations.py "data/stations.csv" || true
python3 -m uvicorn main:app --reload --port 8001 &
GEO_PID=$!
cd ..

echo " "
echo "✅ 모든 서비스가 성공적으로 구동되었습니다!"
echo "👉 웹 브라우저를 열고 http://localhost:8000 এ 접속하세요."
echo "   (종료하시려면 'Ctrl + C'를 누르시면 됩니다)"
echo "--------------------------------------"
echo "👇 아래부터는 각 서비스의 실시간 통합 로그가 출력됩니다."

# 무한 대기 (백그라운드로 띄워진 파이썬 앱들의 로그가 터미널에 섞여서 나오게 함)
wait
