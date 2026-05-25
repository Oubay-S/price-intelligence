import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Server render modes. Public pages are rendered on demand (SSR) rather than
 * prerendered: `products/:id` has unbounded params and every page pulls
 * live data from the backend, so a build-time prerender would be stale.
 *
 * Auth-gated routes render client-side: the JWT lives in localStorage, which
 * the server cannot read, so an SSR pass of a guarded route would always fail
 * authGuard and redirect to /login. Client rendering lets the app initializer
 * restore the session before authGuard runs.
 */
export const serverRoutes: ServerRoute[] = [
  { path: 'watchlist', renderMode: RenderMode.Client },
  { path: 'alerts', renderMode: RenderMode.Client },
  { path: 'profile', renderMode: RenderMode.Client },
  {
    path: '**',
    renderMode: RenderMode.Server,
  },
];
