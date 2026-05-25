/**
 * errorInterceptor — global handling for unrecoverable HTTP failures.
 *
 * Registered *before* authInterceptor so it sits on the outside of the chain
 * and only sees the final error — after authInterceptor's silent-refresh retry
 * has had its chance. Responsibilities:
 *
 *   - status 0   → network/offline: toast a connectivity message.
 *   - status 401 → session invalid and unrecoverable: clear it and redirect to
 *                  /login (auth endpoints are skipped — a 401 there is a bad
 *                  login, handled by the form, not a dead session).
 *   - status 5xx → server error: toast.
 *
 * The error is always re-thrown so page-level handlers still render their own
 * error cards. Side effects are browser-only so SSR stays clean.
 */
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AuthService } from '../services/auth.service';
import { ToastService } from '../services/toast.service';

function isAuthEndpoint(url: string): boolean {
  return /\/auth\/(login|register|refresh|token|forgot-password|reset-password)/.test(url);
}

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  const toast = inject(ToastService);
  const auth = inject(AuthService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      if (isBrowser && !isAuthEndpoint(req.url)) {
        if (err.status === 0) {
          toast.error('Network error — check your connection and try again.');
        } else if (err.status === 401) {
          auth.clearSession();
          if (!router.url.startsWith('/login')) {
            router.navigate(['/login'], { queryParams: { returnUrl: router.url } });
          }
        } else if (err.status >= 500) {
          toast.error('Server error — please try again in a moment.');
        }
      }
      return throwError(() => err);
    }),
  );
};
