# Gonggo-zip (공고zip): AI-Powered Housing Announcement Automation System

An intelligent data pipeline that automatically extracts key information from real estate/subscription announcements (PDF, XLSX) using AI (Gemini), updates location data, and calculates walking distances to subway stations via PostGIS.

---

## Key Features

- **Smart Document Parsing**: Instantly structures information such as housing name, units, address, and rent using LLM (Gemini).
- **Dynamic Schema Support**: Captures all available metadata (e.g., parking, elevators, rooms) and displays them in an expandable "More Info" UI.
- **Geo-Enrichment**: Identifies coordinates and calculates the nearest subway station names and actual walking distances via PostGIS.
- **Flexible API Key Management**: Allows users to enter Gemini API keys directly in the web UI and persists them in `localStorage`.
- **Lightweight Architecture**: HTTP-based 2-Agent structure optimized for low-specification servers like Oracle Cloud Always Free.
- **Automated Deployment**: One-click deployment to Oracle Cloud ARM instances using Terraform and GitHub Actions.

---

## System Architecture

The system consists of two independent agents:

1. **Parser Agent (Port 8000)**: 
   - **UI**: Provides file upload, visualization, and map interaction.
   - **Logic**: Text extraction, Gemini API parsing, MongoDB persistence, and Geo Agent orchestration.
2. **Geo Agent (Port 8001)**: 
   - **Enrichment**: Geocoding via Kakao Local API and subway matching via PostGIS spatial queries.
   - **Persistence**: Saves enriched data to PostgreSQL.

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
```

### 3. Execution
```bash
chmod +x start_all.sh
./start_all.sh
```
> The script handles process cleanup, infrastructure startup, dependency installation, and spatial database initialization.

---

## Cloud Deployment

For Oracle Cloud Infrastructure (OCI) Always Free deployment:
- **Terraform**: Use scripts in the `terraform/` directory to provision the instance.
- **CI/CD**: Automatic deployment via `.github/workflows/deploy.yml`.
- **Required Secrets**: Register `OCI_HOST`, `OCI_SSH_KEY`, `DOCKERHUB_USERNAME`, and `DOCKERHUB_TOKEN` in GitHub Secrets.

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
