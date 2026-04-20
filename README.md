# Digital Internal Audit Replica

Production-style full-stack replica of a Digital Internal Audit platform, built from the provided structured analysis report and captured DIA page artifacts.

This implementation recreates the observed product behavior while intentionally improving the control weaknesses identified in the report:

- Backend-enforced RBAC, not menu-only hiding
- Native in-app dashboard instead of an external Power BI login dependency
- Real Initial Data Request and admin routes instead of broken redirects
- Controlled maker-checker workflow for action plans
- Activity logging, notifications, and seeded demo data for realistic UAT

## Assumed Design

The source system left a few workflow areas unclear. These are implemented as explicit `assumed design` improvements:

- `audit_plans` represent the planned universe and feed executable `audits`
- `Initial Data Request` is implemented as a real knowledge-library module
- `Dashboard` is intentionally restricted to Auditor and Super Admin
- Action plan completion requires auditee response to reach `Under Review`
- In-app reporting and charts replace the external BI dependency observed in the source

## Folder Structure

```text
Replica/
├─ apps/
│  ├─ api/
│  │  ├─ alembic/
│  │  ├─ app/
│  │  │  ├─ api/
│  │  │  ├─ core/
│  │  │  ├─ db/
│  │  │  ├─ middleware/
│  │  │  ├─ models/
│  │  │  ├─ repositories/
│  │  │  ├─ schemas/
│  │  │  ├─ services/
│  │  │  └─ utils/
│  │  └─ tests/
│  └─ web/
│     ├─ app/
│     ├─ components/
│     ├─ lib/
│     └─ tests/
├─ storage/
│  └─ uploads/
├─ docker-compose.yml
├─ API_DOCUMENTATION.md
├─ RBAC_MATRIX.md
├─ DATABASE_SCHEMA.md
├─ WORKFLOW_NOTES.md
└─ README.md
```

## Architecture

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, React Hook Form, Zod, TanStack Table, Recharts
- Backend: FastAPI, SQLAlchemy 2.x, Pydantic, Alembic
- Database: PostgreSQL in Docker, SQLite-friendly test setup
- Auth: JWT access and refresh tokens with argon2 password hashing
- Middleware: CORS, correlation ID, normalized errors
- Storage: local file storage abstraction in `storage/uploads`
- Testing: Pytest backend coverage and Playwright E2E specs

## Core Modules

- Dashboard
- Audit Planning Engine
- Manage Audits
- Action Plans
- Reports and exports
- Knowledge Library
- Master Data
- Admin activity logs and user administration

## Local Setup

### 1. Environment

Copy `.env.example` to `.env` and adjust values if needed.

### 2. Backend

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd apps/web
cmd /c npm install
cmd /c npm run dev
```

### 4. Dockerized Setup

The repo is configured for a 2-container local demo stack:

- `app`: combined container running Next.js, FastAPI, nginx reverse proxy, and supervisor
- `db`: PostgreSQL with a persistent Docker volume

Create the environment file first:

```powershell
Copy-Item .env.example .env
```

Start the stack:

```powershell
docker compose --env-file .env up --build
```

Docker startup automatically:

- waits for PostgreSQL to become healthy
- runs `alembic upgrade head`
- seeds demo data with `python -m app.db.seed`
- launches FastAPI, Next.js, and nginx under supervisor

Services:

- App: `http://localhost:3000`
- API docs: `http://localhost:3000/docs`
- Health: `http://localhost:3000/health`

Reset the database completely:

```powershell
docker compose down -v
docker compose --env-file .env up --build
```

If port `3000` is already in use on your machine, change `APP_PORT` in `.env` before starting the stack.

## Demo Users

- `superadmin` / `Password@123`
- `auditoruser1` / `Password@123`
- `auditeeuser1` / `Password@123`

## Useful Commands

### Migrations

```bash
cd apps/api
alembic upgrade head
alembic downgrade -1
```

### Seed Data

```bash
cd apps/api
python -m app.db.seed
```

### Backend Tests

```bash
cd apps/api
pytest
```

### Frontend E2E

```bash
cd apps/web
cmd /c npm install
npx playwright install
cmd /c npm run test:e2e
```

## What the Seed Demonstrates

- Role-specific landing and navigation
- Planned, unplanned, in-progress, and overdue audits
- Action plan states across pending, in progress, reopened, and completed
- Planning records for process risk, ERM risk, initiatives, and overall assessment
- Knowledge library records across process universe, RACM, benchmarks, and IDR
- Activity logs and notifications

## API and Design Notes

- All API routes are versioned under `/api/v1`
- The backend remains the source of truth for authorization and workflow transitions
- Soft delete and audit fields are built into core models
- File uploads are validated for size and content type

See:

- [API_DOCUMENTATION.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/API_DOCUMENTATION.md)
- [RBAC_MATRIX.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/RBAC_MATRIX.md)
- [DATABASE_SCHEMA.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/DATABASE_SCHEMA.md)
- [WORKFLOW_NOTES.md](/D:/AI%20project/Codex/Business%20central%20download%20PI/Replica/WORKFLOW_NOTES.md)
