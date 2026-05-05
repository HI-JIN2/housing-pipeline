# Gonggo-zip (공고zip): AI-Powered Housing Announcement Automation System

An intelligent data pipeline that automatically extracts key information from real estate/subscription announcements (PDF, XLSX) using AI (Gemini), updates location data, and calculates walking distances to subway stations via PostGIS.

---

## Key Features

- **Smart Document Parsing**: Instantly structures information such as housing name, units, address, and rent using LLM (Gemini).
- **Dynamic Schema Support**: Captures all available metadata (e.g., parking, elevators, rooms) and displays them in an expandable "More Info" UI.
- **Geo-Enrichment**: Identifies coordinates and calculates nearest subway stations/distances via PostGIS. Results are visualized instantly during the **Data Preview** stage.
- **SH/LH Notice Monitoring**: Periodically crawls SH and LH notice boards and sends Slack alerts for newly discovered announcements.
- **GitHub Actions Triggering**: In production, GitHub Actions cron calls the notice-agent API instead of keeping a resident scheduler loop on the server.
- **Flexible API Key Management**: Allows users to enter Gemini API keys directly in the web UI and persists them in `localStorage`.
- **Admin Security**: Protects data integrity by requiring an `ADMIN_PASSWORD` for announcement uploads and deletions.
- **Lightweight Architecture**: HTTP-based 2-Agent structure optimized for low-specification servers like Oracle Cloud Always Free.
- **Automated Deployment**: One-click deployment to Oracle Cloud ARM instances using Terraform and GitHub Actions.

---

## System Architecture

The system consists of three independent agents:

1. **Parser Agent (Port 8000)**: 
   - **UI**: Provides file upload, visualization, and map interaction.
   - **Logic**: Text extraction, Gemini API parsing, MongoDB persistence, and Geo Agent orchestration.
2. **Geo Agent (Port 8001)**: 
   - **Enrichment**: Geocoding via Kakao Local API and subway matching via PostGIS spatial queries.
   - **Persistence**: Saves enriched data to PostgreSQL.
3. **Notice Agent (Port 8003)**:
   - **Monitoring API**: Exposes the execution endpoint that crawls SH/LH notice boards and detects newly posted items.
   - **Notification / API**: Sends Slack Incoming Webhook alerts and exposes manual run and recent-history APIs.

---

## Quick Start

### 1. Prerequisites
- Docker Desktop or Docker Engine
- Python 3.10+ (Recommended)
- Google Gemini API Key & Kakao REST API Key

### 2. Environment Setup (.env)
Create a `.env` file in the project root. (Gemini Key can also be entered via the UI.)
```env
# API Keys
GEMINI_API_KEY="your_gemini_key_optional"
KAKAO_REST_API_KEY="your_kakao_key"

# Database Connections
POSTGRES_DSN="postgresql://housing_user:housing_password@127.0.0.1:5433/housing_db"
MONGO_URL="mongodb://127.0.0.1:27017"

# Admin Security
ADMIN_PASSWORD="your_secure_admin_password"

# Slack / Notice Monitoring
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxx/yyy/zzz"
NOTICE_CRAWLER_ENABLED="false"
NOTICE_CRAWL_INTERVAL_SECONDS="3600"
NOTICE_NOTIFY_ON_BOOTSTRAP="false"
NOTICE_AGENT_TOKEN="optional_internal_token"
SH_NOTICE_URL="https://www.i-sh.co.kr/app/lay2/program/S48T561C563/www/brd/m_247/list.do?multi_itm_seq=2"
LH_NOTICE_URL="https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026"

# Local Monitoring
GRAFANA_PASSWORD="your_local_grafana_password"
```

### 3. Execution
```bash
chmod +x start_all.sh
./start_all.sh
```
> The script handles process cleanup, infrastructure startup, dependency installation, and spatial database initialization.

### 4. SH/LH Slack Notice Alerts
- `notice-agent` stores crawl history in MongoDB and only sends Slack alerts for newly inserted notices.
- Local resident scheduling is disabled by default with `NOTICE_CRAWLER_ENABLED=false`.
- Trigger one crawl manually:
```bash
curl -X POST http://localhost:8003/api/notices/run-once
```
- If token protection is enabled:
```bash
curl -X POST http://localhost:8003/api/notices/run-once \
  -H "x-notice-token: your_token"
```
- List recent notices:
```bash
curl "http://localhost:8003/api/notices/recent?limit=20&source=LH"
```

### 5. Production Cron Trigger
- In production, the resident notice-agent loop stays disabled and GitHub Actions calls `POST /api/notices/run-once` on a schedule.
- Workflow file: `.github/workflows/notice-crawl.yml`
- Default schedule: every hour at minute 0 (`0 * * * *`)
- You can also trigger it manually with `workflow_dispatch`.

---

## Cloud Deployment

For Oracle Cloud Infrastructure (OCI) Always Free deployment:
- **Terraform**: Use scripts in the `terraform/` directory to provision the instance.
- **CI/CD**: Automatic deployment via `.github/workflows/deploy.yml`.
- **Required Secrets**: Register `OCI_HOST`, `OCI_SSH_KEY`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `SLACK_WEBHOOK_URL`, `NOTICE_AGENT_TOKEN`, and `NOTICE_AGENT_BASE_URL` in GitHub Secrets.
- **Monitoring Secret**: Set `OCI_MONITORING_SOURCE_CIDR` to the trusted public CIDR allowed to scrape production metrics.

## Monitoring Notes
- Set `GRAFANA_PASSWORD` in `.env` before running `docker compose -f docker-compose.local-monitoring.yml up`.
- Replace `YOUR_PRODUCTION_SERVER_IP` in `deploy/prometheus/prometheus.local.yml` with the actual production host before scraping remote metrics.

---

## Tech Stack
- **Frontend**: React, Vite, Tailwind CSS, Kakao Maps API
- **Backend**: FastAPI, Uvicorn, Motor (Async MongoDB), Asyncpg
- **AI**: Google Gemini API (Generative AI)
- **Database**: MongoDB (Raw/Parsed), PostgreSQL/PostGIS (Enriched)
- **DevOps**: Docker Compose, Terraform (OCI), GitHub Actions

---

## Contribution
Please report any unsupported announcement formats via Issues.
