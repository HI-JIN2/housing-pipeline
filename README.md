# 🏢 Housing Pipeline: AI-Powered Real Estate Dispatcher

부동산/청약 공고문(PDF, XLSX)에서 핵심 정보를 AI(Gemini)로 자동 추출하고, 위치 정보 보강 및 지하철역 도보 거리를 연산해주는 **지능형 주택 공고 분석 파이프라인**입니다.

---

## ✨ Key Features

- **📄 Smart Document Parsing**: PDF 및 엑셀 공고문에서 주택명, 공급호수, 주소, 임대료 등을 LLM(Gemini)으로 즉시 구조화
- **🚄 Geo-Enrichment**: 추출된 주소의 좌표를 찾고, PostGIS를 통해 **가장 가까운 지하철역명과 실제 도보 거리**를 계산
- **🗄️ Flexible Storage**: 가변적인 공고 형식에 대응하기 위해 MongoDB를 사용하며, 동일 공고 재분석 시 비용 절감을 위한 캐싱 적용
- **⚡ Lightweight Architecture**: Kafka/Zookeeper 등 무거운 인프라를 제거한 **HTTP 기반 2-Agent 구조**로 저사양 서버에서도 구동 가능 (Oracle Cloud Always Free 타겟)

---

## 🏗️ Architecture

시스템은 두 개의 독립적인 에이전트로 구성됩니다:

1. **Parser Agent (`:8000`)**: 
   - **UI**: 사용자가 파일을 드래그하여 업로드하고 분석 결과를 시각적으로 확인
   - **Logic**: 문서 텍스트 추출 -> Gemini API 파싱 -> MongoDB 저장 -> Geo Agent 호출
2. **Geo Agent (`:8001`)**: 
   - **Enrichment**: 카카오 로컬 API 지오코딩 + PostGIS 공간 쿼리 (지하철역 매칭)
   - **Persistence**: 보강된 최종 데이터를 PostgreSQL에 저장

---

## 🚀 Quick Start

### 1. 전제 조건 (Prerequisites)
- Docker Desktop (or Docker Engine)
- Python 3.9+ 
- Google Gemini API Key & Kakao REST API Key

### 2. 환경 설정 (.env)
프로젝트 루트에 `.env` 파일을 생성합니다. (또는 `README.md`의 예시 참고)
```env
# API Keys
GEMINI_API_KEY="your_gemini_key"
KAKAO_REST_API_KEY="your_kakao_key"

# Database Connections
POSTGRES_DSN="postgresql://housing_user:housing_password@127.0.0.1:5433/housing_db"
MONGO_URL="mongodb://127.0.0.1:27017"
```

### 3. 원클릭 실행 (One-Step Run)
```bash
chmod +x start_all.sh
./start_all.sh
```
> 스크립트 실행 시 **좀비 프로세스 정리, 인프라 부팅, 의존성 설치, 지하철 역 DB 초기화**가 자동으로 진행됩니다.

---

## ☁️ Cloud Deployment
운영 서버 배포를 위해 다음의 가이드를 제공합니다:
- **Terraform**: [terraform/](file:///Users/yujin/PycharmProjects/housing-pipeline/terraform/) 폴더의 코드를 통해 OCI 인프라 자동 구축 가능
- **배포 가이드**: [production_deployment.md](file:///Users/yujin/.gemini/antigravity/brain/af93b895-4fc5-4130-b641-6d42c35481f9/production_deployment.md) 참고

---

## 🛠️ Tech Stack
- **Backend**: FastAPI, Uvicorn, Motor (Async MongoDB), Asyncpg
- **AI**: Google Gemini API (Generative AI)
- **Database**: MongoDB (Raw/Parsed), PostgreSQL/PostGIS (Enriched)
- **DevOps**: Docker Compose, Terraform (OCI)

---

## 🤝 Contribution
분석이 실패하는 공고문이 있다면 `issues`에 제보해 주세요! 🚀
