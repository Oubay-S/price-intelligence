/**
 * AuthService — owns all authentication state and logic.
 *
 * Responsibilities:
 *  - Persist the access / refresh token pair (localStorage, browser only).
 *  - Expose the current user + auth status as signals for the UI.
 *  - login / register / logout flows.
 *  - Silent token refresh — used by `authInterceptor` on a 401.
 *
 * SSR-safe: every localStorage access is guarded by `isPlatformBrowser`,
 * so the service degrades to "logged out" during server rendering.
 */
import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { Observable, of, tap, throwError } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

import { TokenPair, UserLogin, UserRegister, UserResponse } from '../models';
import { ApiService } from './api.service';

const ACCESS_KEY = 'pi_access_token';
const REFRESH_KEY = 'pi_refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  /** The signed-in user, or null when logged out. */
  readonly currentUser = signal<UserResponse | null>(null);
  /** True once a login/restore has produced a valid session. */
  readonly isAuthenticated = computed(() => this.currentUser() !== null);
  /** Surfaces auth-flow failures to forms (cleared on each new attempt). */
  readonly authError = signal<string | null>(null);

  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    if (this.isBrowser) {
      this.accessToken = localStorage.getItem(ACCESS_KEY);
      this.refreshToken = localStorage.getItem(REFRESH_KEY);
    }
  }

  /** Raw access token — consumed by the interceptor and WebSocketService. */
  getAccessToken(): string | null {
    return this.accessToken;
  }

  /** Restore the session on app start: if a token exists, fetch /auth/me.
   *  Returns an Observable so APP_INITIALIZER-style callers can await it. */
  restoreSession(): Observable<UserResponse | null> {
    if (!this.accessToken) return of(null);
    return this.api.me().pipe(
      tap((user) => this.currentUser.set(user)),
      map((user): UserResponse | null => user),
      catchError(() => {
        // Token expired/invalid — try one refresh, else clear.
        return this.refreshSession().pipe(
          switchMap(() => this.api.me()),
          tap((user) => this.currentUser.set(user)),
          map((user): UserResponse | null => user),
          catchError(() => {
            this.clearTokens();
            return of(null);
          }),
        );
      }),
    );
  }

  register(body: UserRegister): Observable<UserResponse> {
    this.authError.set(null);
    return this.api.register(body).pipe(
      catchError((err) => {
        this.authError.set(this.messageOf(err));
        return throwError(() => err);
      }),
    );
  }

  /** Email/password login. Stores tokens then loads the user profile. */
  login(credentials: UserLogin): Observable<UserResponse> {
    this.authError.set(null);
    return this.api.login(credentials).pipe(
      tap((tokens) => this.storeTokens(tokens)),
      switchMap(() => this.api.me()),
      tap((user) => this.currentUser.set(user)),
      catchError((err) => {
        this.clearTokens();
        this.authError.set(this.messageOf(err));
        return throwError(() => err);
      }),
    );
  }

  /** Revoke the refresh token server-side, then clear local state. */
  logout(): Observable<void> {
    const token = this.refreshToken;
    const finish = () => {
      this.clearTokens();
    };
    if (!token) {
      finish();
      return of(void 0);
    }
    return this.api.logout({ refresh_token: token }).pipe(
      map(() => void 0),
      // Even if the server call fails, log out locally.
      catchError(() => of(void 0)),
      tap(finish),
    );
  }

  /** Exchange the refresh token for a fresh pair. Used by the interceptor. */
  refreshSession(): Observable<TokenPair> {
    if (!this.refreshToken) {
      return throwError(() => new Error('No refresh token'));
    }
    return this.api.refresh({ refresh_token: this.refreshToken }).pipe(
      tap((tokens) => this.storeTokens(tokens)),
      catchError((err) => {
        this.clearTokens();
        return throwError(() => err);
      }),
    );
  }

  /** Clear local session without a server round-trip. Called by the error
   *  interceptor when a 401 is unrecoverable (refresh already failed). */
  clearSession(): void {
    this.clearTokens();
  }

  // --- token persistence -----------------------------------------------------

  private storeTokens(tokens: TokenPair): void {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (this.isBrowser) {
      localStorage.setItem(ACCESS_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    }
  }

  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.currentUser.set(null);
    if (this.isBrowser) {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    }
  }

  private messageOf(err: unknown): string {
    const e = err as { message?: string };
    return e?.message ?? 'Authentication failed. Please try again.';
  }
}
