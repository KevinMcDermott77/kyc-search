# KYC Search Engine

UK Companies House KYC lookup tool. Search companies, view officers, PSCs, filing history, and ownership structure as an org chart.

## Quick Start

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# Edit .env and set CH_API_KEY (leave blank for mock mode)
docker compose up --build
```

- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### Option B — Local Development

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env  # then edit .env
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev  # runs on port 3001
```

You need PostgreSQL and Redis running locally, or update DATABASE_URL/REDIS_URL in .env to point at existing instances.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CH_API_KEY` | _(empty)_ | Companies House API key. If blank, mock mode is used |
| `DATABASE_URL` | postgresql+asyncpg://kyc:kyc_secret@localhost:5432/kyc | Async PostgreSQL connection string |
| `REDIS_URL` | redis://localhost:6379 | Redis for rate limiter |
| `JWT_SECRET` | dev-secret | Change in production |
| `JWT_EXPIRE_MINUTES` | 480 | Token lifetime (8 hours) |
| `ADMIN_EMAIL` | admin@example.com | First admin user (created on startup if no users exist) |
| `ADMIN_PASSWORD` | changeme | First admin password |
| `NEXT_PUBLIC_API_URL` | http://localhost:8000 | Frontend → backend URL |

## Mock Mode

When `CH_API_KEY` is not set, the app runs in mock mode using fixture data:
- Company `00000006` — DEMO HOLDINGS LTD (active, parent company)
- Company `00000007` — DEMO SUBSIDIARY LTD (active, overdue accounts, owned by 00000006)

Search for "demo" to find them.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Current user |
| GET | `/search?q=&page=` | Search companies |
| GET | `/companies/{number}` | Company profile |
| GET | `/companies/{number}/officers` | Officers |
| GET | `/companies/{number}/pscs` | Persons with significant control |
| GET | `/companies/{number}/filings` | Filing history |
| GET | `/ownership/{number}` | Ownership org chart tree |
| GET | `/audit` | Audit log (admin only) |
| GET | `/admin/users` | List users (admin only) |
| POST | `/admin/users` | Create user (admin only) |
| PATCH | `/admin/users/{id}` | Update user (admin only) |

## Architecture

```
kyc-search/
├── docker-compose.yml          — postgres, redis, backend, frontend
├── backend/                    — FastAPI + SQLAlchemy + asyncpg
│   ├── app/
│   │   ├── main.py             — App entrypoint, CORS, lifespan, admin seed
│   │   ├── config.py           — Settings (pydantic-settings, reads .env)
│   │   ├── dependencies.py     — FastAPI deps: auth, CH client
│   │   ├── core/
│   │   │   ├── security.py     — JWT, bcrypt
│   │   │   └── rate_limiter.py — Redis token bucket (600 req/5min)
│   │   ├── db/                 — SQLAlchemy base + async session
│   │   ├── models/             — ORM models (users, companies, officers, pscs, filings, audit_logs)
│   │   ├── schemas/            — Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── companies_house.py  — Real CH API client (httpx + tenacity)
│   │   │   ├── mock_data.py        — Mock client for demo/dev
│   │   │   ├── ingestion.py        — Upsert CH data into DB
│   │   │   ├── ownership_graph.py  — Recursive ownership tree builder
│   │   │   └── risk_flags.py       — Compute OVERDUE_ACCOUNTS, FREQUENT_RESIGNATIONS, etc.
│   │   └── routers/            — auth, search, companies, ownership, audit, admin
│   └── alembic/                — Database migrations
└── frontend/                   — Next.js 15 + TypeScript + Tailwind
    ├── app/
    │   ├── login/              — Login page
    │   ├── search/             — Company search
    │   ├── company/[number]/   — Company detail (tabbed: overview, officers, PSCs, filings, ownership)
    │   └── admin/              — User management + audit log
    ├── components/
    │   ├── layout/             — AuthGuard, Header
    │   ├── company/            — CompanyHeader, RiskBadge, tab components
    │   ├── ownership/          — OwnershipChart (react-organizational-chart), OwnershipNode
    │   └── ui/                 — Badge, Spinner, ErrorBanner
    └── lib/api.ts              — Typed API client
```

## Privacy

Officers and PSCs store only:
- **Date of birth**: month + year only (never day)
- **Address**: service address only (never home address)

These constraints are enforced at the database model level — the fields simply do not exist.

## Risk Flags

| Flag | Description |
|---|---|
| `OVERDUE_ACCOUNTS` | Accounts overdue per CH data |
| `OVERDUE_CS` | Confirmation statement overdue |
| `INSOLVENCY_HISTORY` | Company has insolvency history |
| `FREQUENT_RESIGNATIONS` | 3+ officer resignations in past 12 months |
| `RECENT_OFFICER_CHANGES` | Officer appointments in past 90 days |
| `NO_ACTIVE_PSCS` | No active persons with significant control |
