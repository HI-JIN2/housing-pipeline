# Housing Pipeline: AI 기반 부동산 공고 분석 자동화 시스템

부동산 및 청약 공고문(PDF, XLSX)에서 핵심 정보를 AI(Gemini)로 자동 추출하고, 위치 정보 보강 및 지하철역 도보 거리를 연산하는 지능형 데이터 파이프라인입니다.

English version is available at [README_EN.md](./README_EN.md).

---

## 주요 기능

- **스마트 문서 파싱**: PDF 및 엑셀 공고문에서 주택명, 공급호수, 주소, 임대료 등을 LLM(Gemini)을 활용해 즉시 구조화합니다.
- **지오 데이터 보강**: 추출된 주소의 좌표를 식별하고, PostGIS를 통해 인근 지하철역명 및 실제 도보 거리를 계산합니다.
- **유연한 저장 구조**: 다양한 공고 형식에 대응하기 위해 MongoDB를 사용하며, 재분석 시 비용 절감을 위한 캐싱 기능을 포함합니다.
- **경량 아키텍처**: Kafka와 같은 무거운 인프라 대신 HTTP 기반의 2-Agent 구조를 채택하여 저사양 서버(Oracle Cloud Free Tier 등)에서도 원활하게 구동됩니다.

---

## 시스템 아키텍처

본 시스템은 두 개의 독립적인 에이전트로 구성됩니다:

1. **Parser Agent (8000 포트)**: 
   - **UI**: 파일 드래그 앤 드롭 업로드 및 분석 결과 시각화 기능을 제공합니다.
   - **로직**: 문서 텍스트 추출, Gemini API 연동 파싱, MongoDB 저장 및 Geo Agent를 호출합니다.
2. **Geo Agent (8001 포트)**: 
   - **데이터 보강**: 카카오 로컬 API 지오코딩 및 PostGIS 공간 쿼리를 통한 지하철역 매칭을 수행합니다.
   - **데이터 저장**: 보강된 최종 데이터를 PostgreSQL에 저장합니다.

---

## 시작하기

### 1. 전제 조건
- Docker Desktop 또는 Docker Engine
- Python 3.9 이상
- Google Gemini API Key 및 카카오 REST API Key

### 2. 환경 설정 (.env)
프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다.
```env
# API Key 설정
GEMINI_API_KEY="발급받은_Gemini_키"
KAKAO_REST_API_KEY="발급받은_카카오_키"

# 데이터베이스 연결 정보
POSTGRES_DSN="postgresql://housing_user:housing_password@127.0.0.1:5433/housing_db"
MONGO_URL="mongodb://127.0.0.1:27017"
```

### 3. 실행 방법
```bash
chmod +x start_all.sh
./start_all.sh
```
> 실행 스크립트는 프로세스 정리, 인프라 구동, 의존성 설치 및 지하철역 데이터베이스 초기화를 자동으로 수행합니다.

---

## 클라우드 배포
운용 환경 배포를 위해 다음 가이드를 참고하십시오:
- **Terraform**: `terraform/` 디렉토리의 코드를 통해 OCI 인프라를 자동으로 구축할 수 있습니다.
- **배포 가이드**: `production_deployment.md`에서 상세 내용을 확인할 수 있습니다.

---

## 기술 스택
- **Backend**: FastAPI, Uvicorn, Motor (Async MongoDB), Asyncpg
- **AI**: Google Gemini API (Generative AI)
- **Database**: MongoDB (Raw/Parsed), PostgreSQL/PostGIS (Enriched)
- **DevOps**: Docker Compose, Terraform (OCI)

---

## 기여하기
분석이 원활하지 않은 공고문 형식이 있다면 Issue를 통해 제보해 주시기 바랍니다.
