/**
 * Development environment (used by `ng serve`).
 *
 * The dev server runs on :4200 and talks straight to the FastAPI backend
 * on :8000, bypassing the reverse proxy. REST routers are mounted under
 * `/api`; WebSockets stay at `/ws` (unprefixed). CORS on the backend must
 * allow http://localhost:4200.
 */
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000/api',
  wsBaseUrl: 'ws://localhost:8000',
};
