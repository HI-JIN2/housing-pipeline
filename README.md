# 공고zip: AI 기반 주택청약 공고 분석 자동화 시스템

SH, LH 주택 청약 공고문(PDF, XLSX)에서 핵심 정보를 LLM(Gemini)으로 자동 추출하고, 위치 정보 보강 및 지하철역 도보 거리를 연산하는 지능형 데이터 파이프라인입니다.

English version is available at [README_EN.md](./README_EN.md).

---

## 주요 기능

- **스마트 문서 파싱**: PDF 및 엑셀 공고문에서 주택명, 공급호수, 주소, 임대료 등을 LLM(Gemini)을 활용해 파싱 및 구조화합니다.
- **다이나믹 스키마 지원**: nosql를 활용해 공고문마다 다른 상세 정보(주차대수, 승강기여부, 방개수 등)를 빠짐없이 추출하여 '더보기' 섹션에 표시합니다.
- **GEO 데이터 보강**: 추출된 주소의 좌표를 식별하고, PostGIS를 통해 인근 지하철역명 및 실제 도보 거리를 계산합니다. (데이터 프리뷰 단계에서 즉시 시각화)
- **SH/LH 공고 모니터링**: SH, LH 공고 게시판을 주기적으로 크롤링하고 신규 공고를 Slack으로 자동 전송합니다.
- **GitHub Actions 트리거**: 운영 환경에서는 상주 스케줄러 대신 GitHub Actions cron이 notice-agent 수동 실행 API를 호출합니다.
- **유연한 API 키 관리**: `.env`에 Gemini 키가 설정되어 있지 않아도, 웹 UI에서 직접 입력하고 브라우저(`localStorage`)에 저장하여 사용할 수 있습니다.
- **관리자 보안**: 공고 업로드 및 삭제 시 `ADMIN_PASSWORD`를 통한 인증을 거쳐 데이터 무결성을 보호합니다.
- **경량 아키텍처**: HTTP 기반의 2-Agent 구조를 채택하여 저사양 서버(Oracle Cloud Free Tier 등)에서도 원활하게 구동됩니다.
- **배포 자동화**: Terraform과 GitHub Actions를 통해 Oracle Cloud ARM 인스턴스에 원클릭으로 배포할 수 있습니다.

---

## 시스템 아키텍처

본 시스템은 세 개의 독립적인 에이전트로 구성됩니다:

1. **Parser Agent (8000 포트)**: 
   - **UI**: 파일 업로드, 분석 결과 시각화, 지도 인터렉션 기능을 제공합니다.
   - **로직**: 문서 텍스트 추출, Gemini API 연동 파싱, MongoDB 저장 및 Geo Agent를 호출합니다.
2. **Geo Agent (8001 포트)**: 
   - **데이터 보강**: 카카오 로컬 API 지오코딩 및 PostGIS 공간 쿼리를 통한 지하철역 매칭을 수행합니다.
   - **데이터 저장**: 보강된 최종 데이터를 PostgreSQL에 저장합니다.
3. **Notice Agent (8003 포트)**:
   - **모니터링 API**: SH/LH 공고 목록을 수집하고 신규 공고 여부를 판별하는 실행 엔드포인트를 제공합니다.
   - **알림/조회**: Slack Incoming Webhook으로 신규 공고를 보내고, 수동 실행 및 최근 공고 조회 API를 제공합니다.

---

## 시작하기

### 1. 전제 조건
- Docker Desktop 또는 Docker Engine
- Python 3.10 이상 권장
- Google Gemini API Key 및 카카오 REST API Key

### 2. 환경 설정 (.env)
프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다.

| 변수명 | 필수 여부 | 설명 |
| :--- | :---: | :--- |
| `KAKAO_REST_API_KEY` | **필수** | 지오코딩 및 지하철역 검색용 카카오 로컬 API 키 |
| `ADMIN_PASSWORD` | **필수** | 관리자 인증용 비밀번호 |
| `GEMINI_API_KEY` | 선택 | Gemini API 키 (미설정 시 UI에서 입력 가능) |
| `GRAFANA_PASSWORD` | 선택 | Grafana 관리자 비밀번호 (로컬 모니터링 사용 시 `.env`에 설정 권장) |
| `SLACK_WEBHOOK_URL` | 선택 | 신규 SH/LH 공고를 보낼 Slack Incoming Webhook URL |
| `NOTICE_CRAWLER_ENABLED` | 선택 | `true`면 notice-agent가 백그라운드 스케줄러로 주기 수집 실행 |
| `NOTICE_CRAWL_INTERVAL_SECONDS` | 선택 | notice-agent 수집 주기(초), 기본값 `3600` |
| `NOTICE_NOTIFY_ON_BOOTSTRAP` | 선택 | 첫 시드 수집 때도 Slack 알림을 보낼지 여부, 기본값 `false` |
| `NOTICE_AGENT_TOKEN` | 선택 | notice-agent 수동 실행/조회 API 보호용 내부 토큰 |
| `SH_NOTICE_URL` | 선택 | SH 공고 목록 URL 커스텀 값 |
| `LH_NOTICE_URL` | 선택 | LH 공고 목록 URL 커스텀 값 |
| `POSTGRES_DSN` | 선택 | 선택 시 직접 설정 (기본값 제공됨) |
| `MONGO_URL` | 선택 | 선택 시 직접 설정 (기본값 제공됨) |
| `MONITORING_SOURCE_CIDR` | 선택 | 운영 메트릭 포트(8001-8002)에 접근할 수 있는 신뢰 CIDR. Terraform/OCI 배포 시 사용 |

### 3. 실행 방법
```bash
chmod +x start_all.sh
./start_all.sh
```
> 실행 스크립트는 프로세스 정리, 인프라 구동, 의존성 설치 및 지하철역 데이터베이스 초기화를 자동으로 수행합니다.

### 4. SH/LH 공고 Slack 알림
- `notice-agent`는 MongoDB에 수집 이력을 저장하고 새로 들어온 공고만 Slack으로 전송합니다.
- 로컬 기본값은 `NOTICE_CRAWLER_ENABLED=false`라서 상주 스케줄러가 꺼져 있습니다.
- 수동 1회 실행:
```bash
curl -X POST http://localhost:8003/api/notices/run-once
```
- 토큰을 설정한 경우:
```bash
curl -X POST http://localhost:8003/api/notices/run-once \
  -H "x-notice-token: your_token"
```
- 최근 수집 공고 조회:
```bash
curl "http://localhost:8003/api/notices/recent?limit=20&source=SH"
```

### 5. 운영 크론 실행 방식
- 운영에서는 `notice-agent` 내부 루프를 켜지 않고, GitHub Actions 스케줄 워크플로우가 `POST /api/notices/run-once`를 호출합니다.
- 워크플로우 파일: `.github/workflows/notice-crawl.yml`
- 기본 스케줄: 매시 정각 (`0 * * * *`)
- 필요 시 GitHub Actions `workflow_dispatch`로 수동 실행도 가능합니다.

---

## 클라우드 배포

Oracle Cloud Infrastructure (OCI) Always Free 티어 배포를 위해 다음을 이용하세요:
- **Terraform**: `terraform/` 디렉토리 코드를 통해 인프라를 구축합니다.
- **CI/CD**: `.github/workflows/deploy.yml`을 통해 자동 배포를 수행합니다.
- **필요 시크릿 (GitHub Secrets)**:
  - 인프라: `OCI_HOST`, `OCI_SSH_KEY`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
  - 앱 설정: `KAKAO_REST_API_KEY`, `ADMIN_PASSWORD`, `KAKAO_JS_KEY`, `SLACK_WEBHOOK_URL`, `NOTICE_AGENT_TOKEN`
  - 크롤링 트리거: `NOTICE_AGENT_BASE_URL` (예: `http://YOUR_SERVER_IP:8003`)
  - 모니터링: `GRAFANA_PASSWORD` (선택), `OCI_MONITORING_SOURCE_CIDR` (운영 메트릭 접근 허용 CIDR)

---

## 모니터링 및 메트릭

저사양 VM(1GB RAM) 환경에서도 안정적으로 구동되는 모니터링 시스템을 포함하고 있습니다.
- **Prometheus (9090)**: 에이전트들의 실시간 상태 및 메트릭 수집
- **Grafana (3000)**: 수집된 데이터 시각화 (`GRAFANA_PASSWORD`로 관리자 비밀번호 설정)
- **OCI Monitoring**: 클라우드 네이티브 메트릭 연동 (Terraform으로 활성화)
- **최적화**: Docker 리소스 제한(128MB) 및 수집 주기(30s) 조정을 통해 OOM 방지

로컬 모니터링 실행 전 확인사항:
- `docker-compose.local-monitoring.yml`은 `.env`의 `GRAFANA_PASSWORD`를 사용합니다.
- `deploy/prometheus/prometheus.local.yml`의 `YOUR_PRODUCTION_SERVER_IP`를 실제 운영 서버 주소로 교체한 뒤 실행해야 합니다.

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
