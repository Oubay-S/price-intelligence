/**
 * ApiService — the single HTTP gateway to the FastAPI backend.
 *
 * Every endpoint is exposed as an Observable. No token handling lives
 * here: the bearer header is attached by `authInterceptor`, and
 * `AuthService` orchestrates login/refresh. This service is pure
 * request/response plumbing plus error normalisation.
 *
 * Base URL comes from `environment.apiBaseUrl` (dev → http://localhost:8000,
 * prod → /api behind the reverse proxy).
 */
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  AlertsResponse,
  ApiError,
  BrandRankingsResponse,
  CompareResponse,
  ErrorEnvelope,
  ForgotPasswordRequest,
  MessageResponse,
  PaginatedProducts,
  PriceDropParams,
  PriceHistory,
  PriceHistoryParams,
  ProductFilterParams,
  ProductResponse,
  ProductStats,
  RefreshRequest,
  ResendVerificationRequest,
  ResetPasswordRequest,
  SupplementCategory,
  TokenPair,
  TrendingResponse,
  UserLogin,
  UserRegister,
  UserResponse,
  VerifyEmailRequest,
  WatchlistAdd,
  WatchlistItemResponse,
  WatchlistListResponse,
  WatchlistUpdate,
} from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  // =========================================================================
  // Auth — /auth/*
  // =========================================================================

  register(body: UserRegister): Observable<UserResponse> {
    return this.post<UserResponse>('/auth/register', body);
  }

  login(body: UserLogin): Observable<TokenPair> {
    return this.post<TokenPair>('/auth/login', body);
  }

  refresh(body: RefreshRequest): Observable<TokenPair> {
    return this.post<TokenPair>('/auth/refresh', body);
  }

  logout(body: RefreshRequest): Observable<MessageResponse> {
    return this.post<MessageResponse>('/auth/logout', body);
  }

  me(): Observable<UserResponse> {
    return this.get<UserResponse>('/auth/me');
  }

  verifyEmail(body: VerifyEmailRequest): Observable<MessageResponse> {
    return this.post<MessageResponse>('/auth/verify-email', body);
  }

  resendVerification(body: ResendVerificationRequest): Observable<MessageResponse> {
    return this.post<MessageResponse>('/auth/resend-verification', body);
  }

  forgotPassword(body: ForgotPasswordRequest): Observable<MessageResponse> {
    return this.post<MessageResponse>('/auth/forgot-password', body);
  }

  resetPassword(body: ResetPasswordRequest): Observable<MessageResponse> {
    return this.post<MessageResponse>('/auth/reset-password', body);
  }

  // =========================================================================
  // Products — /products/*
  // =========================================================================

  /** Paginated catalogue. Backend filters by site/category/page/limit;
   *  finer filters (price/brand) are applied client-side. */
  getProducts(filters: ProductFilterParams = {}): Observable<PaginatedProducts> {
    return this.get<PaginatedProducts>('/products', this.toParams(filters));
  }

  searchProducts(
    q: string,
    opts: { page?: number; limit?: number; category?: SupplementCategory } = {},
  ): Observable<PaginatedProducts> {
    return this.get<PaginatedProducts>('/products/search', this.toParams({ q, ...opts }));
  }

  getTrending(
    period: '24h' | '7d' | '30d' = '24h',
    opts: { category?: SupplementCategory; limit?: number } = {},
  ): Observable<TrendingResponse> {
    return this.get<TrendingResponse>('/products/trending', this.toParams({ period, ...opts }));
  }

  getProduct(productId: string): Observable<ProductResponse> {
    return this.get<ProductResponse>(`/products/${encodeURIComponent(productId)}`);
  }

  // =========================================================================
  // Prices — /prices/*
  // =========================================================================

  getPriceDrops(params: PriceDropParams = {}): Observable<AlertsResponse> {
    return this.get<AlertsResponse>('/prices/drops', this.toParams(params));
  }

  /** Cross-site comparison for up to 4 product IDs. */
  comparePrices(productIds: string[]): Observable<CompareResponse> {
    let httpParams = new HttpParams();
    for (const id of productIds) {
      httpParams = httpParams.append('product_ids', id);
    }
    return this.get<CompareResponse>('/prices/compare', httpParams);
  }

  getPriceHistory(productId: string, params: PriceHistoryParams = {}): Observable<PriceHistory> {
    return this.get<PriceHistory>(
      `/prices/${encodeURIComponent(productId)}/history`,
      this.toParams(params),
    );
  }

  // =========================================================================
  // Stats — /stats/*
  // =========================================================================

  getBrandRankings(category: SupplementCategory): Observable<BrandRankingsResponse> {
    return this.get<BrandRankingsResponse>('/stats/brands', this.toParams({ category }));
  }

  getProductStats(productId: string): Observable<ProductStats> {
    return this.get<ProductStats>(`/stats/${encodeURIComponent(productId)}`);
  }

  // =========================================================================
  // Watchlist — /watchlist/* (all require a valid bearer token)
  // =========================================================================

  getWatchlist(page = 1, limit = 50): Observable<WatchlistListResponse> {
    return this.get<WatchlistListResponse>('/watchlist', this.toParams({ page, limit }));
  }

  addToWatchlist(productId: string, body: WatchlistAdd): Observable<WatchlistItemResponse> {
    return this.post<WatchlistItemResponse>(
      `/watchlist/${encodeURIComponent(productId)}`,
      body,
    );
  }

  updateWatchlistItem(
    productId: string,
    body: WatchlistUpdate,
  ): Observable<WatchlistItemResponse> {
    return this.patch<WatchlistItemResponse>(
      `/watchlist/${encodeURIComponent(productId)}`,
      body,
    );
  }

  removeFromWatchlist(productId: string): Observable<void> {
    return this.delete<void>(`/watchlist/${encodeURIComponent(productId)}`);
  }

  // =========================================================================
  // Health — /health
  // =========================================================================

  health(): Observable<unknown> {
    return this.get<unknown>('/health');
  }

  // =========================================================================
  // Low-level verb helpers
  // =========================================================================

  private get<T>(path: string, params?: HttpParams): Observable<T> {
    return this.http
      .get<T>(this.base + path, { params })
      .pipe(catchError((e) => this.handleError(e)));
  }

  private post<T>(path: string, body: unknown): Observable<T> {
    return this.http
      .post<T>(this.base + path, body)
      .pipe(catchError((e) => this.handleError(e)));
  }

  private patch<T>(path: string, body: unknown): Observable<T> {
    return this.http
      .patch<T>(this.base + path, body)
      .pipe(catchError((e) => this.handleError(e)));
  }

  private delete<T>(path: string): Observable<T> {
    return this.http
      .delete<T>(this.base + path)
      .pipe(catchError((e) => this.handleError(e)));
  }

  /** Serialise a plain object into HttpParams, skipping null/undefined and
   *  expanding array values into repeated params. */
  private toParams(obj: object): HttpParams {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(obj)) {
      if (value === null || value === undefined || value === '') continue;
      if (Array.isArray(value)) {
        for (const v of value) params = params.append(key, String(v));
      } else {
        params = params.set(key, String(value));
      }
    }
    return params;
  }

  /** Map an HttpErrorResponse into the project's normalised `ApiError`. */
  private handleError(err: HttpErrorResponse): Observable<never> {
    let apiError: ApiError;
    const envelope = err.error as ErrorEnvelope | undefined;

    if (envelope?.error?.code) {
      apiError = {
        status: err.status,
        code: envelope.error.code,
        message: envelope.error.message,
        details: envelope.error.details ?? undefined,
      };
    } else if (err.status === 0) {
      apiError = {
        status: 0,
        code: 'network_error',
        message: 'Cannot reach the server. Check your connection and try again.',
      };
    } else {
      apiError = {
        status: err.status,
        code: 'unknown_error',
        message: err.message || 'Something went wrong.',
      };
    }
    return throwError(() => apiError);
  }
}
