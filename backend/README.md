# PriceRadar — Backend

FastAPI service that powers the PriceRadar frontend: product catalogue and
price history reads from BigQuery, user-facing OLTP state in Postgres
(auth, watchlist, alerts), Redis for caching and WebSocket pub/sub,
SMTP for email notifications, and a `/internal/price-event` ingest that
NiFi pushes into for real-time alert fan-out.

> Repo-wide context (Docker Compose, Airflow, NiFi, dbt, Scrapy, Angular
> frontend) lives in the root `CLAUDE.md`. Read both when working across
> layers.

---

## 1. Quick start

### Option A — Docker Compose (recommended)

The full stack (Postgres × 2, Redis, NiFi, Bigtable emulator, Airflow,
dbt, FastAPI, Angular, Nginx) is wired in the repo-root `docker-compose.yml`.
From the **repo root**:

```bash
# 1. Copy and fill the backend env file
cp backend/.env.example backend/.env
# Edit backend/.env — fill every `<...>` placeholder

# 2. Put your GCP service-account JSON at the repo root
#    (filename must be exactly `gcp-credentials.json` — gitignored)

# 3. Bring everything up
docker-compose up -d --build

# 4. First-time only — stamp the Alembic baseline against the freshly
#    initialised postgres-app database, then apply later migrations
docker-compose exec backend python -m alembic stamp 0001
docker-compose exec backend python -m alembic upgrade head

# 5. Smoke test
curl http://localhost:8000/health/live      # → {"status":"ok"}
```

Service URLs (after `up -d`):

| URL                                | What                                             |
| ---------------------------------- | ------------------------------------------------ |
| `http://localhost/`                | Nginx → Angular SPA (production-shape)           |
| `http://localhost:4200/`           | Angular SPA (direct, dev)                        |
| `http://localhost:8000/`           | FastAPI (direct, dev)                            |
| `http://localhost:8000/docs`       | Swagger UI                                       |
| `http://localhost:8000/redoc`      | ReDoc                                            |
| `http://localhost:8080/`           | Airflow webserver (admin / admin123)             |
| `https://localhost:8443/nifi`      | NiFi UI (admin / adminpassword123)               |

### Option B — Local venv (no Docker for the backend)

The Compose-managed Postgres, Redis, NiFi and Bigtable emulator must
already be running (`docker-compose up -d postgres-app redis nifi
bigtable-emulator`). Then:

```powershell
cd backend
python -m venv venv                               # first time only
.\venv\Scripts\Activate.ps1                       # Windows; macOS/Linux: source venv/bin/activate
python -m pip install -r requirements.txt

# Copy + fill the env file (DATABASE_URL points at localhost:5432, etc.)
Copy-Item .env.example .env
# Edit .env

# Run
python -m alembic upgrade head                    # fresh DB
# OR for an already-seeded DB:
python -m alembic stamp 0001
python -m alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

The venv on the maintainer's machine is Python 3.14 and is **not**
auto-activated — `venv\Scripts\` is not on PATH. Either activate first
or invoke the venv's Python directly: `.\venv\Scripts\python.exe -m uvicorn
app.main:app --reload`.

---

## 2. Directory layout

```
backend/
├── Dockerfile                 # python:3.10-slim base; HEALTHCHECK → /health/live
├── requirements.txt
├── alembic.ini                # config; revisions in alembic/versions/
├── pytest.ini
├── .env.example               # template — copy to .env and fill in
├── alembic/
│   └── versions/
│       ├── 0001_baseline.py                       # runs sql/first_setup.sql
│       └── 0002_watchlist_target_price_and_views.py
├── sql/
│   ├── first_setup.sql        # full Postgres schema; auto-run by postgres-app
│   │                          # on its first volume init via docker-entrypoint-initdb.d
│   └── migrations/            # legacy raw SQL — kept for reference
└── app/
    ├── main.py                # FastAPI app factory, lifespan, middleware, exception handlers
    ├── config.py              # pydantic-settings Settings singleton
    ├── database.py            # psycopg2 ThreadedConnectionPool + get_db / get_cursor
    ├── api_responses.py       # ErrorEnvelope + ERR_* response examples for /docs
    ├── models/                # Pydantic v2 — request/response shapes
    │   ├── product.py         # Product, PriceEvent, PaginatedProducts, …
    │   ├── user.py            # UserRegister, TokenPair, VerifyEmailRequest, …
    │   ├── alerts.py, price.py, stats.py, filters.py, integration.py, enums.py
    ├── repositories/          # All SQL.  Returns dict rows; never raises HTTPException
    │   ├── user_repo.py, session_repo.py, refresh_token_repo.py
    │   ├── email_token_repo.py    # email verification + password reset
    │   ├── watchlist_repo.py, alert_repo.py, audit_repo.py, auth_query_repo.py
    ├── routers/               # HTTP / WebSocket handlers
    │   ├── health.py          # /health, /health/live, /health/ready
    │   ├── auth.py            # /auth/* (register, login, refresh, verify, reset, …)
    │   ├── products.py        # /products, /products/search, /products/trending
    │   ├── prices.py          # /prices/drops, /prices/compare, /prices/{id}/history
    │   ├── watchlist.py       # GET/POST/PATCH/DELETE /watchlist
    │   ├── stats.py           # /stats/brands, /stats/{product_id}
    │   ├── internal.py        # /internal/price-event  (NiFi → FastAPI)
    │   └── websocket.py       # /ws/live-prices, /ws/alerts/{user_id}
    ├── services/              # Business logic / orchestration (no SQL, no HTTP)
    │   ├── auth.py            # bcrypt + JWT helpers
    │   ├── session_service.py # login / refresh / logout flows
    │   ├── email.py           # SMTP client + ThreadPoolExecutor
    │   ├── email_templates.py # HTML/plain templates (verification, reset, price drop)
    │   ├── email_tasks.py     # non-blocking helpers: send_verification, send_reset, …
    │   ├── email_flow.py      # verify-email + forgot/reset orchestration
    │   ├── alert_service.py   # price-event fan-out (WebSocket + email fallback)
    │   ├── watchlist_service.py, compare_service.py, analytics.py
    │   ├── bigquery.py, cache.py, websocket.py
    │   └── exceptions.py
    ├── middleware/
    │   └── core.py            # JWT dependency, slowapi limiter, request logging
    └── tests/                 # pytest — see § 7
```

`app/`, `app/middleware/`, and `app/services/` are intentionally **namespace
packages** (no `__init__.py`); don't add one.

---

## 3. Architecture in one screen

```
┌────────────────────────────────────────────────────────────────────────┐
│                            Angular SPA                                 │
│  HTTP /api/*  +  WebSocket /ws/*    (via Nginx reverse proxy on :80)   │
└──────────────────────┬────────────────────────────┬────────────────────┘
                       │                            │
                       ▼                            ▼
              ┌────────────────────┐       ┌────────────────────┐
              │   FastAPI routers  │       │   WebSocket mgr    │
              │  auth / products / │◄──────┤  (in-process)      │
              │  prices / wlist /  │       └────────┬───────────┘
              │  stats / internal  │                │
              └─────┬──────────┬───┘                │
                    │          │                    │
       ┌────────────▼──┐  ┌────▼─────────┐  ┌───────▼────────────┐
       │  Services     │  │ Repositories │  │  Email thread pool │
       │  (business    │  │  (psycopg2   │  │  smtplib → Mailtrap│
       │   logic)      │  │   SQL only)  │  │  /Resend           │
       └────┬──────────┘  └──────┬───────┘  └────────────────────┘
            │                    │
            ▼                    ▼
   ┌────────────────┐   ┌───────────────────┐
   │   BigQuery     │   │   PostgreSQL      │
   │ (product mart) │   │ (users, sessions, │
   │  read-only     │   │  watchlist,       │
   │                │   │  alerts, tokens)  │
   └────────────────┘   └───────────────────┘

NiFi ───POST /internal/price-event───►  alert_service
                                          │
                                          ├── WebSocket /ws/alerts/{user_id} (online users)
                                          └── Email   (offline users — Mailtrap/Resend)
```

### Two stores, two purposes

| Store         | Holds                                                                            |
| ------------- | -------------------------------------------------------------------------------- |
| **Postgres**  | users, sessions, refresh_tokens, user_preferences, watchlist_items, price_alerts, email_verification_tokens, password_reset_tokens, audit_logs |
| **BigQuery**  | product catalogue + price history produced by Scrapy → NiFi/Airflow → dbt        |

`watchlist_items.canonical_product_id` is **not** an FK — it points across
to the BigQuery mart, the join happens in the service layer. When adding
endpoints, decide upfront which store owns the data; never cross-write.

### Connection pool

`app/database.py` uses **`psycopg2.pool.ThreadedConnectionPool`** directly
(no SQLAlchemy in `requirements.txt`). The pool is created in the FastAPI
lifespan, torn down on shutdown. Endpoints get a connection with
`Depends(get_db)` (raw connection) or `get_cursor()` (`RealDictCursor`).
Both auto-commit on success and rollback on exception.

> ⚠️ `DATABASE_URL` must use the plain `postgresql://` scheme. The
> SQLAlchemy-style `postgresql+psycopg2://` is **rejected** by raw
> psycopg2's libpq parser.

---

## 4. Configuration

Every runtime knob lives in `backend/.env` and is loaded through
`app.config.Settings` (pydantic-settings, cached singleton). See
[`.env.example`](.env.example) for every variable with inline
explanations.

Required fields (no defaults — Settings init crashes if missing):
`GCP_PROJECT_ID`, `BIGQUERY_DATASET`, `BIGQUERY_TABLE`,
`GOOGLE_APPLICATION_CREDENTIALS`, `SECRET_KEY`, `DATABASE_URL`,
`REDIS_URL`, `NIFI_URL`.

When running under Compose, the backend service's `environment:` block
**overrides** any host-specific values from `.env`: the DB host becomes
`postgres-app`, Redis becomes `redis`, the credential path becomes
`/opt/gcp/gcp-credentials.json`, etc.

---

## 5. Database migrations (Alembic)

Baseline schema is in `backend/sql/first_setup.sql`. Postgres-app runs
it automatically on first start via `/docker-entrypoint-initdb.d`.
Every change after that goes through Alembic.

```
alembic/versions/
├── 0001_baseline.py                                # = first_setup.sql
└── 0002_watchlist_target_price_and_views.py       # watchlist.target_price + helper views
```

### Fresh database (clean volume)

```powershell
python -m alembic upgrade head      # runs baseline + every later revision
```

### Existing dev database (volume already initdb'd from first_setup.sql)

Stamp baseline first so Alembic doesn't try to re-run it, then apply the rest:

```powershell
python -m alembic stamp 0001
python -m alembic upgrade head
```

### Add a new revision

```powershell
python -m alembic revision -m "add column foo to bar"
# Edit alembic/versions/XXXX_*.py — write upgrade() / downgrade() with op.execute(...)
python -m alembic upgrade head
git add alembic/versions/XXXX_*.py && git commit
```

Autogenerate is **disabled** — every revision is hand-written SQL via
`op.execute(...)` (the project uses raw psycopg2, no ORM models).

---

## 6. Endpoints

OpenAPI / Swagger UI: **http://localhost:8000/docs** (interactive,
generated from FastAPI routes).

### Health

| Method | Path             | Notes                                                     |
| ------ | ---------------- | --------------------------------------------------------- |
| GET    | `/health`        | Legacy liveness alias                                     |
| GET    | `/health/live`   | Liveness — answers 200 as long as the process is up       |
| GET    | `/health/ready`  | Readiness — pings Postgres + Redis + BigQuery; 503 on any |

### Auth — `/auth`

| Method | Path                       | Notes                                                                                          |
| ------ | -------------------------- | ---------------------------------------------------------------------------------------------- |
| POST   | `/auth/register`           | Create user + send verification email (rate-limited)                                           |
| POST   | `/auth/login`              | JSON body, returns access + refresh JWT pair                                                   |
| POST   | `/auth/token`              | OAuth2 password flow (form-encoded variant of /login)                                          |
| POST   | `/auth/refresh`            | Rotate refresh token; reuse = entire session revoked                                           |
| POST   | `/auth/logout`             | Revoke current session + kill all its refresh tokens (auth required)                           |
| GET    | `/auth/me`                 | Current user profile (auth required)                                                           |
| POST   | `/auth/verify-email`       | Redeem the token from the verification email                                                   |
| POST   | `/auth/resend-verification`| Re-send verification mail — always 200 (no enumeration leak)                                   |
| POST   | `/auth/forgot-password`    | Request reset link — always 200                                                                |
| POST   | `/auth/reset-password`     | Redeem reset token + set new password + revoke every session / refresh token                   |

### Products — `/products`

| Method | Path                       | Notes                                                       |
| ------ | -------------------------- | ----------------------------------------------------------- |
| GET    | `/products`                | Paginated list (`page`, `limit`, `site`, `category`)        |
| GET    | `/products/search`         | Title/brand match (`q`, `page`, `limit`, `category`)        |
| GET    | `/products/trending`       | Top movers (`period` ∈ {24h,7d,30d}, `category`, `limit`)   |
| GET    | `/products/{product_id}`   | Single product latest snapshot                              |

### Prices — `/prices`

| Method | Path                              | Notes                                                |
| ------ | --------------------------------- | ---------------------------------------------------- |
| GET    | `/prices/drops`                   | Recent price drops                                   |
| GET    | `/prices/compare`                 | Multi-product side-by-side compare (1–4 ids)         |
| GET    | `/prices/{product_id}/history`    | Daily price history for a product                    |

### Watchlist — `/watchlist` (auth required, per-user RLS)

| Method | Path                            | Notes                                                |
| ------ | ------------------------------- | ---------------------------------------------------- |
| GET    | `/watchlist`                    | Current user's watchlist + per-item unread badge     |
| POST   | `/watchlist/{product_id}`       | Add product to watchlist; optional threshold/target  |
| PATCH  | `/watchlist/{product_id}`       | Update threshold / target / alert_enabled            |
| DELETE | `/watchlist/{product_id}`       | Remove from watchlist                                |

### Stats — `/stats`

| Method | Path                       | Notes                                       |
| ------ | -------------------------- | ------------------------------------------- |
| GET    | `/stats/brands`            | Brand ranking from `mart_brand_rankings`    |
| GET    | `/stats/{product_id}`      | Per-product stats from `mart_product_stats` |

### Internal (NiFi → FastAPI) — `/internal`

| Method | Path                      | Notes                                                                |
| ------ | ------------------------- | -------------------------------------------------------------------- |
| POST   | `/internal/price-event`   | NiFi ingest. Gated by `X-Internal-Key` = `INTERNAL_API_KEY`          |

The handler invalidates Redis caches for the product, broadcasts on
`/ws/live-prices`, evaluates every watchlist row that subscribes, snapshots
fired alerts into `price_alerts`, fans them out to `/ws/alerts/{user_id}`,
and emails users whose live socket count is 0 (offline fallback).

### WebSocket channels

| URL                                | Channel                                                        |
| ---------------------------------- | -------------------------------------------------------------- |
| `ws://localhost:8000/ws/live-prices` | Global feed — every price event for every product            |
| `ws://localhost:8000/ws/alerts/{user_id}` | Per-user feed — only events matching the user's watchlist |

---

## 7. Email service

Email powers three flows: verification, password reset, offline price-drop
alerts. SMTP is synchronous (`smtplib`) so every send runs on a private
`ThreadPoolExecutor` — request handlers hand off the message and return
immediately; a slow SMTP server cannot block the FastAPI event loop.

```
routers/auth.py
services/email_flow.py    ── verify / forgot / reset orchestration
services/email_tasks.py   ── high-level helpers (send_verification_email_task, …)
services/email.py         ── EmailService + ThreadPoolExecutor + singleton
services/email_templates.py  ── HTML + plain-text builders
```

### Mailtrap (dev / testing)

1. Sign in at https://mailtrap.io → Testing → Inboxes → My Inbox.
2. Inside the inbox, **Show Credentials → SMTP Settings**, pick
   **Integrations → Generic / SMTP**.
3. Copy `Host`, `Port`, `Username`, `Password` into `backend/.env`.
4. Restart the backend. Every email lands in the Mailtrap inbox UI;
   nothing is actually delivered.

### Resend (production)

Switch four `.env` values:

```env
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USERNAME=resend
SMTP_PASSWORD=<your-resend-api-key>
EMAIL_FROM_ADDRESS=no-reply@<your-verified-domain>
```

`EMAIL_FROM_ADDRESS` must be on a domain you've verified in the Resend
dashboard (SPF + DKIM DNS records). Gmail / outlook.com `From:` addresses
are rejected.

### Disabling email in CI

Set `EMAIL_ENABLED=false` — every send becomes a no-op (logged at INFO).

---

## 8. Testing

Pytest is in `requirements.txt`. Run from `backend/`:

```powershell
.\venv\Scripts\python.exe -m pytest                  # all tests
.\venv\Scripts\python.exe -m pytest tests/test_auth.py
.\venv\Scripts\python.exe -m pytest -k "watchlist"   # filter by name
```

Tests live in `backend/tests/`. `tests/conftest.py` sets up fixtures.
Integration tests assume Postgres and Redis are reachable (start them
with `docker-compose up -d postgres-app redis`).

---

## 9. Conventions

- **Absolute imports inside `app/`** — `from app.config import settings`,
  never `from .config import settings`.
- **All SQL lives in `app/repositories/*`.** Routers never build SQL
  strings; services never import psycopg2 directly.
- **All inbound shapes are Pydantic models**, all responses use
  `response_model=...` so the schema appears in `/docs`.
- **Error envelope.** Every error response conforms to
  `{"error": {"code": "...", "message": "...", "details": [...]?}}`
  via the exception handlers in `app/main.py`. Use the `ERR_*` constants
  from `app/api_responses.py` in `responses=` so Swagger picks them up.
- **Currency is USD throughout.** Conversion happens upstream in dbt;
  `PriceInfo.currency_raw` keeps the original scrape currency for
  reference only.
- **`/internal/*` is network-internal.** It must never appear in the CORS
  allowlist and must always be gated by `INTERNAL_API_KEY` in prod.

---

## 10. Troubleshooting

| Symptom                                                                     | Likely cause / fix                                                                                                                                          |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pydantic.ValidationError: Field required ... SECRET_KEY` at startup        | `.env` not picked up. Either you copied it to the wrong dir or pydantic can't find it. It must sit at `backend/.env` (next to `requirements.txt`).         |
| `psycopg2.OperationalError: connection to server ... failed`                | Postgres-app is down OR `DATABASE_URL` uses `postgresql+psycopg2://` (SQLAlchemy syntax). Strip the `+psycopg2`.                                            |
| Backend container in restart loop, logs show `/health/ready` 503            | You're using `/health/ready` for the Docker healthcheck; readiness pings BigQuery which isn't reachable locally. Use `/health/live`.                        |
| Verification email never arrives in Mailtrap                                | `SMTP_USERNAME` / `SMTP_PASSWORD` mismatch. Each inbox has its own creds — click *Reset credentials* in Mailtrap if unsure.                                 |
| `/auth/verify-email` always returns 400 invalid                             | Frontend stripped the token from the URL, or `FRONTEND_URL` mismatch means the link points at a different host than the SPA is served from.                 |
| `/internal/price-event` 401 from NiFi                                       | Add `X-Internal-Key: $INTERNAL_API_KEY` header in the NiFi InvokeHTTP processor.                                                                            |
| Alembic `target database is not up to date`                                 | You're on a clean DB but ran `upgrade head` without ever stamping. Run `alembic stamp 0001` first if `first_setup.sql` already created the schema.          |

---

## 11. Where to look next

- `app/main.py` — app factory, middleware, exception handlers
- `app/config.py` — every env var and its default
- `backend/sql/first_setup.sql` — full Postgres schema with comments
- Repo-root `CLAUDE.md` — broader platform (Compose, Airflow, NiFi, dbt, Scrapy, frontend)
- `backend/CLAUDE.md` — backend-specific architecture notes for contributors
