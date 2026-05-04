# AGENTS.md

For agentic coding tools: how to run/build/lint/test, plus repo conventions.

## Layout

- `parser-agent/`: FastAPI (8000) upload + parse (Gemini) + Mongo; calls `geo-agent/`.
- `geo-agent/`: FastAPI (8001) geocode (Kakao) + nearest station (PostGIS); saves to Postgres.
- `shared/`: Pydantic models shared between agents.
- `frontend/`: React + Vite + TypeScript; `/api` proxied to parser in dev + prod.
- `docker-compose.yml`: local Mongo + PostGIS.
- `deploy/docker-compose.prod.yml`: production compose (images + nginx).
- `terraform/`: OCI infra; `terraform.tfstate*` is present (treat as generated; do not hand-edit).

Cursor/Copilot rules: none found (`.cursor/rules/`, `.cursorrules`, `.github/copilot-instructions.md`).

## Local Dev

- Create root `.env` (do not commit): `KAKAO_REST_API_KEY` required; `GEMINI_API_KEY` optional; optional `POSTGRES_DSN`, `MONGO_URL`, `GEO_AGENT_URL`.
- Run everything: `chmod +x start_all.sh && ./start_all.sh`
- URLs: frontend http://localhost:5173, parser http://localhost:8000/api/health, geo http://localhost:8001/api/health

Environment variables used by services:
- `KAKAO_REST_API_KEY`: required for real Kakao geocoding (Geo Agent).
- `GEMINI_API_KEY`: optional; if missing, UI can send a key per request.
- `POSTGRES_DSN`: defaults to `postgresql://housing_user:housing_password@127.0.0.1:5433/housing_db`.
- `MONGO_URL`: defaults to `mongodb://127.0.0.1:27017` / `mongodb://localhost:27017`.
- `GEO_AGENT_URL`: defaults to `http://localhost:8001/api/enrich`.

## Commands

All-in-one:
- `./start_all.sh` (starts infra + both agents + frontend; re-installs deps each run)

Infrastructure (Docker):
- Start DBs: `docker-compose up -d`
- Stop DBs: `docker-compose stop`
- Reset volumes (destructive): `docker-compose down -v`

Health checks:
- Parser: `curl -s http://localhost:8000/api/health`
- Geo: `curl -s http://localhost:8001/api/health`

Parser Agent:
- Install: `python3 -m pip install -r parser-agent/requirements.txt`
- Dev: `python3 -m uvicorn parser-agent.main:app --reload --port 8000`

Geo Agent:
- Install: `python3 -m pip install -r geo-agent/requirements.txt`
- Load stations (optional): `python3 geo-agent/scripts/load_stations.py "geo-agent/data/stations.csv"`
- Dev: `python3 -m uvicorn geo-agent.main:app --reload --port 8001`

Frontend:
- Install: `npm --prefix frontend install`
- Dev: `npm --prefix frontend run dev`
- Build: `npm --prefix frontend run build`
- Preview: `npm --prefix frontend run preview`
- Lint: `npm --prefix frontend run lint`
- Lint single file: `npx --prefix frontend eslint src/App.tsx`
- Typecheck only: `npx --prefix frontend tsc -b -p tsconfig.app.json`

Production (Docker):
- Build images (optional): `docker build -f parser-agent/Dockerfile -t housing-parser .`
- Build images (optional): `docker build -f geo-agent/Dockerfile -t housing-geo .`
- Build images (optional): `docker build -f frontend/Dockerfile -t housing-frontend .`
- Run prod compose: `docker compose --env-file .env -f deploy/docker-compose.prod.yml up -d`

Tests:
- Not wired yet (no `pytest`/`tests/`, and no frontend `test` script).
- If adding pytest: `pytest`, `pytest path/to/test_file.py`, `pytest path/to/test_file.py -k test_name`
- If adding vitest: `npm --prefix frontend run test`, `npm --prefix frontend run test -- -t "test name"`

Terraform (OCI):
- Format: `terraform -chdir=terraform fmt -recursive`
- Validate: `terraform -chdir=terraform validate`
- Plan/apply: prefer CI; do not hand-edit `terraform/terraform.tfstate*`.

GitHub Actions (context):
- `.github/workflows/deploy.yml` builds/pushes Docker images and deploys via SSH.
- It injects the Kakao JS key into `frontend/index.html` by replacing `YOUR_KAKAO_JS_KEY_PLACEHOLDER`.

Suggested local sanity checks (until tests exist):
- Frontend: `npm --prefix frontend run lint && npx --prefix frontend tsc -b -p tsconfig.app.json`
- Python syntax: `python3 -m compileall parser-agent geo-agent shared`
- Docker infra: `docker-compose up -d && docker-compose ps`

Manual smoke test (happy path):
- Start services (`./start_all.sh`), open frontend, upload 1 PDF/XLSX.
- Verify preview renders, save succeeds, and list reload shows enriched fields.
- Verify map markers appear for items with coordinates.

## Style

General:
- Keep diffs small; avoid drive-by refactors.
- Never commit secrets or local state: `.env`, API keys, `frontend/node_modules/`, `frontend/dist/`, `terraform/terraform.tfstate*`.
- Keep API paths stable: `/api/...` (frontend expects this).
- Prefer making changes in the owning component/service (parser vs geo vs frontend) instead of cross-cutting edits.

Git / commits:
- Commit messages use a conventional tag like `feat:`, `fix:`, `chore:` and then a concise Korean description.
- Pull request titles should follow the same convention as commit messages, for example `feat: ...`, `fix: ...`, `refactor: ...`, rather than custom prefixes like `[codex]`.
- Pull request bodies should use `.github/pull_request_template.md` and be written in Korean.
- Pull request bodies must be filled with the actual change details; do not leave template sections blank.
- Pull request bodies should explicitly cover problem/context, what changed, impact, and validation results for the current diff.
- If the user says `코리`, treat it as a request to check code review feedback, apply the fixes, run reasonable validation, then commit and push the changes on the current branch unless the user says otherwise.
- If the user says `달팽이`, treat it as a default workflow trigger: pull latest `main`, create a new branch from that updated `main`, then do the requested work and finish with commit, push, and PR creation unless the user says otherwise.

Python (`parser-agent/`, `geo-agent/`, `shared/`):
- Imports: stdlib, third-party, local; avoid circular imports (prefer moving helpers into `services/`).
- Formatting: 4-space indent; prefer f-strings; keep functions focused.
- Types: add type hints; validate external inputs via `shared/models.py`; prefer specific exceptions (`pydantic.ValidationError`, asyncpg errors).
- Async/IO: keep IO handlers async; use `httpx.AsyncClient()` with explicit timeouts; asyncpg queries parameterized (`$1`, `$2`, ...).
- Errors: raise `fastapi.HTTPException` with correct status; do not `except Exception: pass`; if skipping a record, log id/title/address.
- Logging: code currently uses `print(...)`; if introducing `logging`, keep it consistent within the touched file.

Python naming:
- Modules/files: `snake_case.py`; classes: `PascalCase`; functions/vars: `snake_case`; constants: `UPPER_SNAKE_CASE`.
- FastAPI routes: keep handler names unique within a module (avoid duplicate `health_check`).

Python error-handling expectations:
- Never silently ignore parse/validation failures; if skipping, log the identifying fields.
- For user-facing request failures, return an HTTP status + short `detail` string (no stack traces, no secrets).
- Use retries/backoff only around transient IO (DB startup, network); do not retry validation.

Python project conventions:
- Shared contract: update/add fields in `shared/models.py` first, then adapt both agents.
- FastAPI: keep routes under `/api/...`; avoid breaking existing response shapes used by the frontend.
- Lifespan: services initialize connection pools in lifespan and close on shutdown; avoid leaking pools.
- DB: use asyncpg pool + parameterized SQL; prefer `ON CONFLICT ... DO UPDATE` for idempotent upserts.
- HTTP: set explicit timeouts on outbound calls; do not hang requests indefinitely.
- Imports: this repo sometimes uses `sys.path.append(...)` for `shared/`; avoid expanding this pattern unless necessary (Docker uses `PYTHONPATH`).

TypeScript/React (`frontend/`):
- TypeScript is strict (`frontend/tsconfig.app.json`); avoid `any` (isolate at boundaries like Kakao SDK).
- ESLint is configured (`frontend/eslint.config.js`); keep React Hooks deps correct.
- Imports: external first, then local; avoid unnecessary side-effect imports.
- Formatting: no Prettier; match the file style (many files use semicolons).
- Naming: components `PascalCase`; functions/handlers `camelCase`; types `PascalCase`.
- UI: prefer `cn(...)` for Tailwind class merging; split huge components; keep mobile + desktop working.
- API: use relative `/api/...`; show user-friendly errors and also `console.error` for debug.

TypeScript naming and types:
- Components: `PascalCase`; hooks: `useX`; event handlers: `onX`/`handleX`.
- Prefer `unknown` over `any` for untrusted payloads, then narrow.
- Keep request/response shapes typed (define `interface`/`type` near the API boundary).

Frontend project conventions:
- Proxying: dev uses Vite proxy in `frontend/vite.config.ts`; prod uses nginx proxy in `frontend/nginx.conf`.
- API keys: Kakao Maps JS key is loaded via script tag in `frontend/index.html` (CI replaces placeholder in deploy).
- Maps: Kakao SDK typing is intentionally loose; keep `any` confined to the `window.kakao` boundary.
- Large components: `frontend/src/App.tsx` is big; when adding features, prefer extracting new components into `frontend/src/components/`.
