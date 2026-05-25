import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';

/**
 * Application routes. Every page is lazy-loaded as a standalone component
 * so each feature ships in its own chunk. Watchlist is gated by authGuard.
 */
export const routes: Routes = [
  {
    path: '',
    title: 'PriceIntelligent — Never pay full price on gear',
    loadComponent: () =>
      import('./features/landing/landing-page/landing-page').then((m) => m.LandingPageComponent),
  },
  {
    path: 'products',
    title: 'Catalogue — PriceIntelligent',
    loadComponent: () =>
      import('./features/products/product-catalog/product-catalog').then(
        (m) => m.ProductCatalogComponent,
      ),
  },
  {
    path: 'products/:id',
    title: 'Product — PriceIntelligent',
    loadComponent: () =>
      import('./features/products/product-detail/product-detail').then(
        (m) => m.ProductDetailComponent,
      ),
  },
  {
    path: 'analytics',
    title: 'Market analytics — PriceIntelligent',
    loadComponent: () =>
      import('./features/analytics/analytics-dashboard/analytics-dashboard').then(
        (m) => m.AnalyticsDashboardComponent,
      ),
  },
  {
    path: 'compare',
    title: 'Compare prices — PriceIntelligent',
    loadComponent: () =>
      import('./features/compare/compare-page/compare-page').then((m) => m.ComparePageComponent),
  },
  {
    path: 'watchlist',
    title: 'Watchlist — PriceIntelligent',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/watchlist/watchlist-page/watchlist-page').then(
        (m) => m.WatchlistPageComponent,
      ),
  },
  {
    path: 'alerts',
    title: 'Price drops — PriceIntelligent',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/alerts/alerts-page/alerts-page').then((m) => m.AlertsPageComponent),
  },
  {
    path: 'profile',
    title: 'Account — PriceIntelligent',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/profile/profile-page/profile-page').then((m) => m.ProfilePageComponent),
  },
  {
    path: 'login',
    title: 'Sign in — PriceIntelligent',
    loadComponent: () =>
      import('./features/auth/login-page/login-page').then((m) => m.LoginPageComponent),
  },
  {
    path: 'register',
    title: 'Create account — PriceIntelligent',
    loadComponent: () =>
      import('./features/auth/register-page/register-page').then((m) => m.RegisterPageComponent),
  },
  { path: '**', redirectTo: '' },
];
