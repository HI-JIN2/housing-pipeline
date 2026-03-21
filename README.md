# Housing Pipeline: AI 기반 부동산 공고 분석 자동화 시스템

부동산 및 청약 공고문(PDF, XLSX)에서 핵심 정보를 AI(Gemini)로 자동 추출하고, 위치 정보 보강 및 지하철역 도보 거리를 연산하는 지능형 데이터 파이프라인입니다.

English version is available at [README_EN.md](./README_EN.md).

---

## 주요 기능

- **스마트 문서 파싱**: PDF 및 엑셀 공고문에서 주택명, 공급호수, 주소, 임대료 등을 LLM(Gemini)을 활용해 즉시 구조화합니다.
- **다이내믹 스키마 지원**: 공고문마다 다른 상세 정보(주차대수, 승강기여부, 방개수 등)를 빠짐없이 추출하여 '더보기' 섹션에 표시합니다.
- **지오 데이터 보강**: 추출된 주소의 좌표를 식별하고, PostGIS를 통해 인근 지하철역명 및 실제 도보 거리를 계산합니다.
- **유연한 API 키 관리**: 서버에 Gemini 키가 설정되어 있지 않아도, 웹 UI에서 직접 입력하고 브라우저(`localStorage`)에 저장하여 사용할 수 있습니다.
- **경량 아키텍처**: HTTP 기반의 2-Agent 구조를 채택하여 저사양 서버(Oracle Cloud Free Tier 등)에서도 원활하게 구동됩니다.
- **배포 자동화**: Terraform과 GitHub Actions를 통해 Oracle Cloud ARM 인스턴스에 원클릭으로 배포할 수 있습니다.

---

## 시스템 아키텍처

본 시스템은 두 개의 독립적인 에이전트로 구성됩니다:

1. **Parser Agent (8000 포트)**: 
   - **UI**: 파일 업로드, 분석 결과 시각화, 지도 인터렉션 기능을 제공합니다.
   - **로직**: 문서 텍스트 추출, Gemini API 연동 파싱, MongoDB 저장 및 Geo Agent를 호출합니다.
2. **Geo Agent (8001 포트)**: 
   - **데이터 보강**: 카카오 로컬 API 지오코딩 및 PostGIS 공간 쿼리를 통한 지하철역 매칭을 수행합니다.
   - **데이터 저장**: 보강된 최종 데이터를 PostgreSQL에 저장합니다.

---

## 시작하기

### 1. 전제 조건
- Docker Desktop 또는 Docker Engine
- Python 3.10 이상 권장
- Google Gemini API Key 및 카카오 REST API Key

### 2. 환경 설정 (.env)
프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다. (Gemini 키는 웹 UI에서 직접 입력할 수도 있습니다.)
```env
# API Key 설정
GEMINI_API_KEY="발급받은_Gemini_키 (선택)"
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

Oracle Cloud Infrastructure (OCI) Always Free 티어 배포를 위해 다음을 이용하세요:
- **Terraform**: `terraform/` 디렉토리의 코드를 통해 인프라를 구축합니다.
- **CI/CD**: `.github/workflows/deploy.yml`을 통해 자동 배포를 수행합니다.
- **필요 시크릿**: `OCI_HOST`, `OCI_SSH_KEY`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`을 GitHub Secrets에 등록하십시오.

---

## 기술 스택
- **Frontend**: React, Vite, Tailwind CSS, Kakao Maps API
- **Backend**: FastAPI, Uvicorn, Motor (Async MongoDB), Asyncpg
- **AI**: Google Gemini API (Generative AI)
- **Database**: MongoDB (Raw/Parsed), PostgreSQL/PostGIS (Enriched)
- **DevOps**: Docker Compose, Terraform (OCI), GitHub Actions

---

## 기여하기
분석이 원활하지 않은 공고문 형식이 있다면 Issue를 통해 제보해 주시기 바랍니다.
