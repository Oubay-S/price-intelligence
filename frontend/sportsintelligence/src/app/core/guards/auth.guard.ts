/**
 * authGuard — protects routes that need a signed-in user.
 *
 * Watchlist and alerts require a session. If the user isn't authenticated
 * the guard redirects to /login, preserving the intended URL in
 * `returnUrl` so the login page can bounce back after success.
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url },
  });
};
