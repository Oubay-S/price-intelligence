/**
 * authInterceptor — attaches the bearer token and handles 401s.
 *
 * Outbound: if an access token exists and the request targets our API,
 * add `Authorization: Bearer <token>`.
 *
 * Inbound 401: attempt a single silent refresh, then replay the original
 * request with the new token. Concurrent 401s share one refresh call.
 * Auth endpoints themselves are never retried (a 401 there is terminal).
 */
import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';

import { AuthService } from '../services/auth.service';

/** Single in-flight refresh shared across concurrent 401s. */
let refreshInFlight: Observable<unknown> | null = null;

function isAuthEndpoint(url: string): boolean {
  return /\/auth\/(login|register|refresh|token|forgot-password|reset-password)/.test(url);
}

function withBearer(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.getAccessToken();

  const authed = token ? withBearer(req, token) : req;

  return next(authed).pipe(
    catchError((err: HttpErrorResponse) => {
      const isRetryable =
        err.status === 401 && !!auth.getAccessToken() && !isAuthEndpoint(req.url);

      if (!isRetryable) {
        return throwError(() => err);
      }

      // Coalesce concurrent refreshes into one.
      if (!refreshInFlight) {
        refreshInFlight = auth.refreshSession();
      }

      return refreshInFlight.pipe(
        switchMap(() => {
          refreshInFlight = null;
          const fresh = auth.getAccessToken();
          return next(fresh ? withBearer(req, fresh) : req);
        }),
        catchError((refreshErr) => {
          refreshInFlight = null;
          return throwError(() => refreshErr);
        }),
      );
    }),
  );
};
