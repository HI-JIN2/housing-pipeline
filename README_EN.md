# Housing Pipeline: AI-Powered Real Estate Dispatcher

An intelligent housing announcement analysis pipeline that automatically extracts key information from real estate/subscription announcements (PDF, XLSX) using AI (Gemini), updates location data, and calculates walking distances to subway stations.

---

## Key Features

- **Smart Document Parsing**: Instantly structures information such as housing name, number of units, address, and rent from PDF and Excel announcements using LLM (Gemini).
- **Geo-Enrichment**: Identifies coordinates for extracted addresses and calculates the nearest subway station names and actual walking distances via PostGIS.
- **Flexible Storage**: Uses MongoDB to handle variable announcement formats and implements caching to reduce costs when re-analyzing the same announcement.
- **Lightweight Architecture**: An HTTP-based 2-Agent structure that removes heavy infrastructure like Kafka/Zookeeper, suitable for low-specification servers (targeting Oracle Cloud Always Free).

---

## Architecture

The system consists of two independent agents:

1. **Parser Agent (Port 8000)**: 
   - **UI**: Allows users to upload files via drag-and-drop and visually confirm analysis results.
   - **Logic**: Extracts document text, parses via Gemini API, stores in MongoDB, and calls the Geo Agent.
2. **Geo Agent (Port 8001)**: 
   - **Enrichment**: Performs geocoding via Kakao Local API and executes PostGIS spatial queries for subway station matching.
   - **Persistence**: Saves the final enriched data to PostgreSQL.

---

## Quick Start

### 1. Prerequisites
- Docker Desktop (or Docker Engine)
- Python 3.9+ 
- Google Gemini API Key & Kakao REST API Key

### 2. Environment Setup (.env)
Create a `.env` file in the project root.
```env
# API Keys
GEMINI_API_KEY="your_gemini_key"
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
> The script automatically handles process cleanup, infrastructure startup, dependency installation, and subway station database initialization.

---

## Cloud Deployment
Refer to the following guides for production deployment:
- **Terraform**: Use the code in the `terraform/` directory for automated OCI infrastructure setup.
- **Deployment Guide**: See `production_deployment.md` for details.

---

## Tech Stack
- **Backend**: FastAPI, Uvicorn, Motor (Async MongoDB), Asyncpg
- **AI**: Google Gemini API (Generative AI)
- **Database**: MongoDB (Raw/Parsed), PostgreSQL/PostGIS (Enriched)
- **DevOps**: Docker Compose, Terraform (OCI)

---

## Contribution
Please report any failed announcement analyses via issues.
