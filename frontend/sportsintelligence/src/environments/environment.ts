/**
 * Production environment.
 *
 * Served behind the reverse-proxy Nginx, which routes `/api/*` and
 * `/ws/*` to the FastAPI backend on the same origin. The backend mounts
 * its REST routers under `/api`, so this base URL lines up end to end.
 */
export const environment = {
  production: true,
  apiBaseUrl: '/api',
  /** Empty = derive ws origin from window.location at runtime. */
  wsBaseUrl: '',
};
