# Housing Pipeline 프로젝트 🏢

부동산/청약 공고문(PDF, XLSX)을 업로드하면, 완전히 자동으로 **데이터 구조화**부터 **위치 정보 기반 검색/보강**까지 수행해 주는 2-Agent 하우징 데이터 파이프라인입니다. 

## 시스템 구조 (Architecture)

1. **Parser Agent (`localhost:8000`)** 
   - 사용자가 문서를 업로드하는 프론트엔드 UI를 제공합니다.
   - 업로드된 문서에서 `pdfplumber` / `openpyxl`을 활용해 텍스트를 추출합니다.
   - 추출된 데이터를 **Google Gemini API** (무료 LLM)를 거쳐 지정된 JSON 스키마 형태로 파싱해 줍니다.
   - 이 파싱된 데이터(호수, 가격, 주소 등)를 `parsed_data` Kafka 토픽으로 송신합니다.
2. **Geo Agent (`localhost:8001` - Background)**
   - Kafka를 실시간으로 구독하며 새 부동산 매물이 들어올 때마다 동작합니다.
   - **카카오 Local API**를 이용해 주소를 위경도 좌표로 변환(Geocoding)합니다.
   - **PostGIS**를 활용하여 가장 가까운 인접 지하철역과 도보 최단 거리 및 시간을 계산합니다.
   - 위치 정보 캐싱(Location Cache)을 통해 이미 조회한 이력이 있는 주소의 중복 호출을 방지합니다.
3. **인프라 (Docker-Compose)**
   - `Zookeeper` & `Kafka`: 두 Agent 간의 메시지 브로커 역할
   - `PostGIS`: 지리 정보 보강을 위한 공간(Spatial) 쿼리 제공 관계형 데이터베이스

---

## 🚀 빠른 시작 (Quick Start)

이 프로젝트는 macOS 환경에 최적화된 통합 실행 스크립트(`start_all.sh`)를 제공합니다. 터미널 탭을 여러 개 관리할 필요 없이 명령어 한 번으로 모든 백그라운드 인프라와 2개의 서버를 동시에 구동할 수 있습니다.

### 1. 환경 설정 (.env)
프로젝트 최상단 루트 디렉토리에 `.env` 파일을 만들고 아래 정보들을 채워주세요.
```env
# Google Gemini LLM 파서 설정
GEMINI_API_KEY="AI Studio에서 발급받은 키 입력"

# 카카오 길찾기 API 설정
KAKAO_API_KEY="카카오 디벨로퍼스에서 발급받은 REST API 키 입력"

# 아래는 기본값(로컬) 수정 불필요
KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
POSTGRES_DSN="postgresql://housing_user:housing_password@localhost:5432/housing_db"
```

### 2. 패키지 설치
각 서버가 참조할 파이썬 의존성 패키지들을 모두 설치해주세요. (가상환경 사용을 권장합니다)
```bash
pip install -r parser-agent/requirements.txt
pip install -r geo-agent/requirements.txt
```

### 3. 단일 스크립트로 전체 실행 (Mac 전용)
```bash
./start_all.sh
```
> 도커 컨테이너를 구동한 뒤 파서와 지리정보 에이전트 2개가 동시에 백그라운드로 실행됩니다.  
> 실행 취소를 원하시면 `Ctrl + C`를 누르세요. 안전하게 모든 프로세스가 함께 종료됩니다.

---

## 👩‍💻 사용 방법

1. 브라우저를 열고 `http://localhost:8000`에 접속하면 업로드 UI가 나타납니다.
2. 분석을 원하는 청약 모집공고 `PDF` 문서나 `XLSX` 매물 엑셀을 드래그하여 업로드합니다.
3. UI 화면에서 즉시 **구조화된 JSON 데이터 결과**를 확인합니다.
4. 동시에 `start_all.sh`가 구동중인 터미널 창을 보시면, Geo Agent가 이 데이터를 Kafka로부터 받아 길찾기를 수행하고 실시간으로 PostGIS에 기록하는 로그를 구경하실 수 있습니다!

---

## 🚇 역 데이터 추가 방법 (Optional)
처음 설치 시에는 캐싱용 `강남역` 하나만 등록되어 있습니다. 
만약 전국의 지하철 정보가 담긴 CSV 파일 (`name`, `lat`, `lng` 열 포함)을 구하셨다면 아래 명령어로 한 번에 DB에 밀어 넣으실 수 있습니다.
```bash
python geo-agent/scripts/load_stations.py 다운받은파일명.csv
```
