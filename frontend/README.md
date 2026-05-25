# PriceRadar — Frontend

Angular 21 single-page app for the PriceRadar platform: browse the scraped
product catalogue, inspect per-product price history, compare prices across
stores, run a personal watchlist with target-price alerts, and view the Data
Analyst's market-analytics dashboard. Talks to the FastAPI backend over REST
(`/api/*`) and a WebSocket live feed (`/ws/*`).

> Repo-wide context (Docker Compose, Airflow, NiFi, dbt, Scrapy, BigQuery) is
> in the root `CLAUDE.md`. The backend is documented in `backend/README.md`.
> The Angular project itself lives in `frontend/sportsintelligence/`.

---

## 1. Quick start

### Option A — Docker Compose (recommended)

The frontend is built and served by a multi-stage image (Node 20 build →
nginx serve) wired into the repo-root `docker-compose.yml`. From the **repo
root**:

```bash
docker-compose up -d --build frontend backend
```

Then open **`http://localhost:4200/`**.

The frontend container serves the built app **and** proxies `/api/*` and
`/ws/*` to `backend:8000`, so `:4200` is a fully working entry point on its
own — no dependency on the separate reverse-proxy nginx or host port 80.

| URL                          | What                                              |
| ---------------------------- | ------------------------------------------------- |
| `http://localhost:4200/`     | Angular app (served by the frontend container)    |
| `http://localhost/`          | Same app via the dedicated reverse-proxy nginx¹   |
| `http://localhost:8000/docs` | Backend Swagger UI                                |

> ¹ Port 80 is the *intended* production-shape entry, but it may be taken by a
> host process (e.g. XAMPP/Apache). If `http://localhost/` shows someone
> else's page, stop that process or just use `:4200`.

### Option B — Local dev server (hot reload, no Docker for the frontend)

The backend must be reachable at `http://localhost:8000` (run it via Docker or
a local venv — see `backend/README.md`). Then:

```bash
cd frontend/sportsintelligence
npm install            # first time only
npm start              # ng serve → http://localhost:4200 (hot reload)
```

In dev (`ng serve`) the API base URL is the absolute `http://localhost:8000/api`
(see `environment.development.ts`); the backend CORS allowlist already permits
`http://localhost:4200`.

Other scripts:

```bash
npm run build          # production build into dist/
npm test               # unit tests (Vitest)
npm run watch          # dev build with --watch
```

---

## 2. Directory layout

All app code is under `frontend/sportsintelligence/src/`. Build/serve files
live one level up in `frontend/`.

```
frontend/
├── Dockerfile              # multi-stage: node:20-alpine build → nginx:alpine serve
├── nginx.conf              # frontend container: static serve + /api,/ws proxy
└── sportsintelligence/
    ├── angular.json        # build (server output mode) / test (vitest) targets
    ├── .postcssrc.json     # Tailwind v4 via @tailwindcss/postcss
    └── src/
        ├── main.ts             # browser bootstrap
        ├── main.server.ts      # SSR bootstrap
        ├── server.ts           # Express SSR entry
        ├── styles.css          # global styles + design tokens
        └── app/
            ├── app.ts                  # root shell (navbar + footer + toast + <router-outlet>)
            ├── app.config.ts           # providers: router, http + interceptors, hydration
            ├── app.routes.ts           # route table (lazy standalone components)
            ├── core/
            │   ├── models/             # typed DTOs mirroring backend schemas + enums
            │   ├── services/           # api, auth, theme, toast, websocket, live-feed
            │   ├── guards/             # authGuard
            │   └── interceptors/       # auth.interceptor, error.interceptor
            ├── features/               # one folder per route (lazy-loaded)
            │   ├── landing/  auth/  products/  compare/
            │   ├── analytics/  watchlist/  alerts/  profile/
            └── shared/components/      # navbar, footer, toast, icon, chart,
                                        # loading-skeleton, product-card,
                                        # price-badge, price-chart
```

---

## 3. Architecture in one screen

- **Angular 21, standalone components** — no NgModules. Every route is a
  `loadComponent` lazy chunk (`app.routes.ts`).
- **Signals + `OnPush`** everywhere. Component state is `signal()` /
  `computed()`; change detection is `ChangeDetectionStrategy.OnPush`. This also
  sidesteps the classic `ExpressionChangedAfterItHasBeenChecked` error class.
- **SSR build, CSR serve.** `angular.json` builds in *server output mode*
  (`dist/sportsintelligence/{browser,server}`). In Docker we serve the
  `browser/` bundle statically via nginx and fall back to `index.csr.html`
  (the client-render shell) for any route, so the app hydrates client-side.
  Components are written SSR-safe regardless (`isPlatformBrowser`,
  `afterNextRender`) — e.g. Chart.js and the WebSocket only initialise in the
  browser.
- **One HTTP gateway.** `core/services/api.service.ts` is the only place that
  builds requests. It holds no auth logic — the bearer token is attached by the
  interceptor.
- **Two interceptors** (order matters; registered as
  `[errorInterceptor, authInterceptor]`):
  - `authInterceptor` — attaches `Authorization: Bearer …`; on a 401 it does a
    single silent refresh and replays the request (concurrent 401s share one
    refresh).
  - `errorInterceptor` (outer, sees the *final* error) — toasts on 5xx and
    network/offline errors, and on an unrecoverable 401 clears the session and
    redirects to `/login`.
- **Auth state** lives in `auth.service.ts` as signals (`currentUser`,
  `isAuthenticated`). Tokens persist in `localStorage` (browser-guarded). The
  session is restored before routing via an app initializer so `authGuard` sees
  real state on hard reloads.
- **Styling** — Tailwind v4 (`@tailwindcss/postcss`) plus design tokens /
  component classes in `src/styles.css`.

### Page-state contract

Every data page renders the same four states via Angular control flow
(`@if`/`@else if`/`@for`):

```
@if (loading())        → <app-loading-skeleton>
@else if (error())     → error card + Retry button
@else if (empty)       → empty-state card
@else                  → the data
```

---

## 4. Routes

`app.routes.ts` — every entry is a lazy standalone component with a descriptive
`title` (Angular's default `TitleStrategy` applies it to `<title>`):

| Path             | Component               | Title                         | Auth |
| ---------------- | ----------------------- | ----------------------------- | ---- |
| `/`              | LandingPage             | PriceIntelligent — home       | —    |
| `/products`      | ProductCatalog          | Catalogue                     | —    |
| `/products/:id`  | ProductDetail           | Product                       | —    |
| `/analytics`     | AnalyticsDashboard      | Market analytics              | —    |
| `/compare`       | ComparePage             | Compare prices                | —    |
| `/watchlist`     | WatchlistPage           | Watchlist                     | ✅   |
| `/alerts`        | AlertsPage              | Price drops                   | ✅   |
| `/profile`       | ProfilePage             | Account                       | ✅   |
| `/login`         | LoginPage               | Sign in                       | —    |
| `/register`      | RegisterPage            | Create account                | —    |
| `**`             | → redirect to `/`       |                               |      |

Auth-gated routes use `authGuard` (`core/guards/auth.guard.ts`).

---

## 5. Backend endpoints consumed

All calls go through `ApiService` against `environment.apiBaseUrl`
(`/api` in prod, `http://localhost:8000/api` in dev). The bearer token is
injected by `authInterceptor`.

### Auth — `/auth`
| Method | Path                         | ApiService method      |
| ------ | ---------------------------- | ---------------------- |
| POST   | `/auth/register`             | `register`             |
| POST   | `/auth/login`                | `login`                |
| POST   | `/auth/refresh`              | `refresh`              |
| POST   | `/auth/logout`               | `logout`               |
| GET    | `/auth/me`                   | `me`                   |
| POST   | `/auth/verify-email`         | `verifyEmail`          |
| POST   | `/auth/resend-verification`  | `resendVerification`   |
| POST   | `/auth/forgot-password`      | `forgotPassword`       |
| POST   | `/auth/reset-password`       | `resetPassword`        |

### Products — `/products`
| Method | Path                  | ApiService method | Notes                                   |
| ------ | --------------------- | ----------------- | --------------------------------------- |
| GET    | `/products`           | `getProducts`     | server-side filter/sort/paginate        |
| GET    | `/products/search`    | `searchProducts`  | LIKE on name                            |
| GET    | `/products/trending`  | `getTrending`     | by drop magnitude, window `24h/7d/30d`  |
| GET    | `/products/{id}`      | `getProduct`      | latest snapshot                         |

### Prices — `/prices`
| Method | Path                       | ApiService method  | Notes                       |
| ------ | -------------------------- | ------------------ | --------------------------- |
| GET    | `/prices/drops`            | `getPriceDrops`    | seeds the alerts feed       |
| GET    | `/prices/compare`          | `comparePrices`    | up to 4 `product_ids`       |
| GET    | `/prices/{id}/history`     | `getPriceHistory`  | time series for the chart   |

### Stats — `/stats`
| Method | Path             | ApiService method   |
| ------ | ---------------- | ------------------- |
| GET    | `/stats/brands`  | `getBrandRankings`  |
| GET    | `/stats/{id}`    | `getProductStats`   |

### Watchlist — `/watchlist` (auth required)
| Method | Path                  | ApiService method      |
| ------ | --------------------- | ---------------------- |
| GET    | `/watchlist`          | `getWatchlist`         |
| POST   | `/watchlist/{id}`     | `addToWatchlist`       |
| PATCH  | `/watchlist/{id}`     | `updateWatchlistItem`  |
| DELETE | `/watchlist/{id}`     | `removeFromWatchlist`  |

### Analytics — `/analytics` (Data Analyst dashboard)
| Method | Path                          | ApiService method        |
| ------ | ----------------------------- | ------------------------ |
| GET    | `/analytics/kpis`             | `getAnalyticsKpis`       |
| GET    | `/analytics/price-by-store`   | `getPriceByStore`        |
| GET    | `/analytics/price-by-category`| `getPriceByCategory`     |
| GET    | `/analytics/time-series`      | `getPriceTimeSeries`     |
| GET    | `/analytics/heatmap`          | `getPriceHeatmap`        |
| GET    | `/analytics/top-discounts`    | `getTopDiscounts`        |
| GET    | `/analytics/recommendations`  | `getRecommendations`     |

### WebSocket
| Channel            | Consumed by                 |
| ------------------ | --------------------------- |
| `/ws/live-prices`  | `live-feed.service` → alerts page live feed |

---

## 6. Build & serve (Docker)

`frontend/Dockerfile` is a two-stage build:

1. **Build** (`node:20-alpine`) — `npm ci` then `npm run build` (production)
   → `dist/sportsintelligence/browser`.
2. **Serve** (`nginx:alpine`) — copies `browser/` to `/usr/share/nginx/html`,
   removes the stock nginx `index.html`, and installs `frontend/nginx.conf`.

`frontend/nginx.conf` does three things:

- serves static assets with long-lived cache headers,
- SPA fallback: any unmatched route → `index.csr.html`,
- proxies `/api/*` and `/ws/*` to `backend:8000` (Docker DNS resolver +
  variable `proxy_pass` so nginx starts even if the backend isn't up yet).

Healthcheck uses busybox `wget` against `127.0.0.1` (nginx:alpine has no curl,
and `localhost` resolves to IPv6 which nginx doesn't listen on).

---

## 7. Categories

The catalogue category filter mirrors the **actual** scraped data in BigQuery.
Only six categories exist and each maps to a raw value (mapping lives in
`backend/app/services/bigquery.py`):

| UI label       | enum value           | raw BigQuery category |
| -------------- | -------------------- | --------------------- |
| Gym            | `strength_home_gym`  | `gym`, `general`      |
| Football       | `team_football`      | `football`            |
| Basketball     | `team_basketball`    | `basketball`          |
| Volleyball     | `team_volleyball`    | `Volleyball`          |
| Racket Sports  | `team_racket`        | `Racket-Sports`       |
| Combat Sports  | `combat_boxing_mma`  | `combat-sports`       |

Keep `SUPPLEMENT_CATEGORIES` / `CATEGORY_LABELS` in
`core/models/enums.ts` in sync with the backend `SupplementCategory` enum.

---

## 8. Testing

Unit tests run on **Vitest** via the Angular `unit-test` builder
(`tsconfig.spec.json` includes `src/**/*.spec.ts`, globals enabled):

```bash
cd frontend/sportsintelligence
npm test                                       # all specs
npm test -- --include src/app/.../foo.spec.ts  # single spec
```

CI runs `npm run test -- --watch=false`. At least one spec must exist or the
builder errors with `No tests found`.

---

## 9. Conventions

- **Standalone components only** — declare deps in the component `imports`
  array; no NgModules.
- **Signals for state**, `computed()` for derived values, `OnPush` change
  detection.
- **Modern control flow** (`@if` / `@for` / `@switch`) — not `*ngIf` / `*ngFor`.
- **SSR-safe side effects** — guard browser-only APIs (`localStorage`,
  `WebSocket`, Chart.js canvas) with `isPlatformBrowser` / `afterNextRender`.
- **All HTTP through `ApiService`**; never call `HttpClient` from a component.
- **Models mirror the backend** — keep `core/models/*` in step with the
  FastAPI Pydantic schemas.

---

## 10. Troubleshooting

| Symptom                                   | Cause / fix                                                                 |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| `:4200` shows "Welcome to nginx"          | Stale image — rebuild: `docker-compose up -d --build frontend`.             |
| App loads but no data (HTML from `/api`)  | Frontend `/api` proxy missing/old — rebuild frontend so `nginx.conf` applies.|
| `http://localhost/` shows another app     | Host port 80 taken (e.g. XAMPP/Apache). Stop it, or use `:4200`.            |
| `:8000/` returns `Not Found`              | Expected — the API has no `/` page. Use `/docs`, `/health`, or `/api/*`.    |
| Analytics page "Couldn't load"            | Backend BigQuery creds — see `backend/README.md` / root `CLAUDE.md`.        |
| Category filter returns nothing           | UI category not in the 6 real ones — see §7.                                |

---

## 11. Where to look next

- `backend/README.md` — API contract, auth, BigQuery, migrations.
- Root `CLAUDE.md` — full platform (Docker, Airflow, NiFi, dbt, Scrapy).
- `src/app/app.config.ts` — providers, interceptor order, hydration.
- `src/app/core/services/api.service.ts` — the full endpoint surface.
