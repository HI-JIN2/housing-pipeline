# Housing Pipeline 프로젝트

부동산/청약 공고문(PDF, XLSX)을 업로드하여 데이터 구조화부터 위치 정보 기반 검색 및 보강을 수행하는 2-Agent 기반 데이터 파이프라인입니다.

## 시스템 구조 (Architecture)

1. **Parser Agent (`localhost:8000`)** 
   - 문서를 쉽게 업로드하고 과거 내역을 조회할 수 있는 웹 UI를 제공합니다.
   - 업로드된 문서에서 `pdfplumber`와 `openpyxl`을 활용해 텍스트를 추출합니다.
   - 추출된 텍스트를 **Google Gemini API**를 통해 지정된 JSON 스키마 형태로 파싱합니다.
   - MongoDB 기반 저장소를 활용하여 다중 형식으로 파싱된 결과를 보관하며, 중복 공고의 문서 캐싱을 통해 인프라 비용을 절감합니다.
   - 구조화된 데이터(호수, 가격, 주소 등)를 분석 즉시 **Geo Agent**의 HTTP 엔드포인트로 전송합니다.

2. **Geo Agent (`localhost:8001`)**
   - Parser Agent로부터 전달받은 주택 데이터를 실시간으로 보강 처리합니다.
   - **카카오 Local API**를 이용해 주소를 지리적 좌표로 변환(Geocoding)합니다.
   - **PostGIS**를 활용하여 가장 가까운 지하철역과 최단 도보 거리를 연산합니다.
   - 위치 정보 캐시를 거쳐 외부 API의 불필요한 호출을 제한합니다.

3. **인프라 (Docker-Compose)**
   - `PostGIS`: 지리 정보 보강을 위한 공간(Spatial) 쿼리 데이터베이스
   - `MongoDB`: 가변적인 JSON 구조에 대응하는 문서 저장소 및 LLM 호출 비용 최적화를 위한 캐시 서버

---

## 빠른 시작 (Quick Start)

단일 실행 스크립트(`start_all.sh`)를 사용하여 백그라운드 인프라와 서버 컴포넌트를 동시에 구동할 수 있습니다.

### 1. 환경 설정 (.env)
루트 디렉토리에 `.env` 파일을 생성하고 아래 설정값을 기입합니다.
```env
# Google Gemini LLM 파서 설정
GEMINI_API_KEY="발급받은 키 입력"

# 카카오 길찾기 API 설정
KAKAO_API_KEY="발급받은 REST API 키 입력"

# 설정 기본값
POSTGRES_DSN="postgresql://housing_user:housing_password@127.0.0.1:5433/housing_db"
MONGO_URL="mongodb://127.0.0.1:27017"
```

### 2. 통합 실행 스크립트 구동
```bash
./start_all.sh
```
> 자동화 스크립트 실행 시 패키지 의존성 설치, PostGIS 역 좌표 데이터 초기 적재가 병렬로 진행되며 서버가 구동됩니다.
> 종료를 원하실 경우 터미널에서 `Ctrl + C`를 입력하여 안전하게 모든 프로세스를 중지시킵니다.

---

## 사용 방법

1. 브라우저에서 `http://localhost:8000`에 접속합니다.
2. 분석 대상인 문서(`PDF` 또는 `XLSX`)를 최대 3개까지 드래그하여 업로드합니다.
3. 웹 UI 화면에서 즉시 구조화된 결과 및 최근 분석 조회 내역을 확인할 수 있습니다.
4. 시스템 커맨드라인 로그를 통해 Geo Agent 측의 데이터베이스 처리 트랜잭션을 실시간 모니터링할 수 있습니다.
