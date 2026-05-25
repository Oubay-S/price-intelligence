/**
 * ProductDetailComponent — single-product view.
 *
 * Pulls three endpoints for the `:id` route param:
 *   GET /products/{id}            — identity, current pricing, attributes
 *   GET /prices/{id}/history      — time-series for the chart
 *   GET /stats/{id}               — descriptive + predictive stats
 *
 * The chart re-fetches when the user switches the time-range tab.
 */
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe, CurrencyPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

import {
  ApiError,
  CATEGORY_LABELS,
  PriceHistory,
  ProductResponse,
  ProductStats,
} from '../../../core/models';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../../../shared/components/icon/icon';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PriceBadgeComponent } from '../../../shared/components/price-badge/price-badge';
import { PriceChartComponent } from '../../../shared/components/price-chart/price-chart';

type Range = '7d' | '30d' | '90d' | 'all';

@Component({
  selector: 'app-product-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    DatePipe,
    DecimalPipe,
    CurrencyPipe,
    IconComponent,
    PriceBadgeComponent,
    PriceChartComponent,
    LoadingSkeletonComponent,
  ],
  template: `
    <div class="page fade-up">
      <div class="container ph-layout">
        <div>
          @if (loading()) {
            <app-loading-skeleton variant="block" height="420px" />
          } @else if (error()) {
            <div class="card empty-state">
              <div class="big">Product not found.</div>
              <div>{{ error()!.message }}</div>
              <a class="btn ghost" style="margin-top:14px" routerLink="/products">
                Back to catalogue
              </a>
            </div>
          } @else if (product(); as p) {
            <div class="card ph-main">
              <div class="hd">
                <div>
                  <div class="mono" style="font-size:11px;letter-spacing:.1em;
                    color:var(--text-faint);text-transform:uppercase">
                    {{ p.brand_raw }} · {{ categoryLabel() }}
                  </div>
                  <h2 class="serif" style="font-size:32px;margin:6px 0 0;
                    letter-spacing:-.02em;font-weight:400">{{ p.name }}</h2>
                </div>
                <div class="range-tabs">
                  @for (r of ranges; track r) {
                    <button [attr.aria-pressed]="range() === r" (click)="setRange(r)">
                      {{ r.toUpperCase() }}
                    </button>
                  }
                </div>
              </div>

              <div class="chart-wrap">
                <div style="display:flex;align-items:baseline;gap:14px;margin-bottom:14px;
                  flex-wrap:wrap">
                  <span class="serif" style="font-size:48px;letter-spacing:-.02em;line-height:1">
                    {{ p.pricing.current | currency: 'MAD' }}
                  </span>
                  <app-price-badge [trend]="p.pricing.trend" [pct]="p.pricing.discount_pct" />
                  @if (history(); as h) {
                    <span class="mono" style="color:var(--text-faint);font-size:12px;
                      margin-left:auto">
                      Low {{ h.min_price | currency: 'MAD' }} ·
                      High {{ h.max_price | currency: 'MAD' }}
                    </span>
                  }
                </div>

                @if (historyLoading()) {
                  <app-loading-skeleton variant="block" height="320px" />
                } @else if (chartValues().length) {
                  <app-price-chart
                    [labels]="chartLabels()"
                    [values]="chartValues()"
                    [median]="history()?.median_price ?? null"
                    seriesLabel="Lowest price (MAD)"
                  />
                } @else {
                  <div class="empty-state" style="padding:40px">
                    No price history recorded for this product yet.
                  </div>
                }
              </div>

              @if (history(); as h) {
                <div class="ph-stats">
                  <div class="stat2">
                    <div class="lbl">Current</div>
                    <div class="num">{{ p.pricing.current | currency: 'MAD' }}</div>
                  </div>
                  <div class="stat2">
                    <div class="lbl">Lowest</div>
                    <div class="num" style="color:var(--success)">
                      {{ h.min_price | currency: 'MAD' }}
                    </div>
                  </div>
                  <div class="stat2">
                    <div class="lbl">Average</div>
                    <div class="num">{{ h.avg_price | currency: 'MAD' }}</div>
                  </div>
                  <div class="stat2">
                    <div class="lbl">Highest</div>
                    <div class="num">{{ h.max_price | currency: 'MAD' }}</div>
                  </div>
                </div>
              }
            </div>
          }
        </div>

        <!-- Right rail -->
        <aside style="display:flex;flex-direction:column;gap:16px">
          @if (product(); as p) {
            <div class="card" style="padding:18px">
              <div style="font-size:13px;font-weight:500;margin-bottom:10px">Quick actions</div>
              <a class="btn primary" style="width:100%;justify-content:center;margin-bottom:8px"
                [routerLink]="['/compare']" [queryParams]="{ ids: p.canonical_product_id }">
                <app-icon name="compare" [size]="14" /> Compare across stores
              </a>
              <button class="btn ghost" style="width:100%;justify-content:center"
                [disabled]="watchlistBusy()" (click)="addToWatchlist(p)">
                <app-icon name="bell" [size]="14" />
                {{ inWatchlist() ? 'On your watchlist' : 'Add to watchlist' }}
              </button>
              <a class="btn quiet" style="width:100%;justify-content:center;margin-top:8px"
                [href]="p.listing_url" target="_blank" rel="noopener">
                Visit listing <app-icon name="arrow-r" [size]="13" />
              </a>
            </div>
          }

          @if (stats(); as s) {
            <div class="card">
              <div style="padding:16px 18px;border-bottom:1px solid var(--line);
                font-size:13px;font-weight:500">
                Statistics · {{ s.period_days }}-day window
              </div>
              <div class="event-item">
                <div class="body">
                  <b>Volatility</b>
                  <div style="color:var(--text-dim);font-size:12px;margin-top:2px">
                    CV {{ s.coefficient_of_variation | number: '1.2-2' }} —
                    {{ s.is_volatile ? 'volatile' : 'steady' }}
                  </div>
                </div>
              </div>
              <div class="event-item">
                <div class="body">
                  <b>Daily velocity</b>
                  <div style="color:var(--text-dim);font-size:12px;margin-top:2px">
                    {{ s.velocity_per_day | currency: 'MAD' }}/day · trend {{ s.price_trend }}
                  </div>
                </div>
              </div>
              @if (s.estimated_floor_30d != null) {
                <div class="event-item">
                  <div class="body">
                    <b>Predicted 30-day floor</b>
                    <div style="color:var(--accent);font-size:12px;margin-top:2px">
                      {{ s.estimated_floor_30d | currency: 'MAD' }}
                    </div>
                  </div>
                </div>
              }
              <div class="event-item">
                <div class="body">
                  <b>Coverage</b>
                  <div style="color:var(--text-dim);font-size:12px;margin-top:2px">
                    {{ s.total_observations | number }} observations ·
                    {{ s.sites_tracked }} sites
                  </div>
                </div>
              </div>
            </div>
          }

          @if (product(); as p) {
            <div class="card" style="padding:18px">
              <div style="font-size:13px;font-weight:500;margin-bottom:8px">Last scraped</div>
              <div class="mono" style="color:var(--text-dim);font-size:12px">
                {{ p.scraped_at | date: 'medium' }}
              </div>
              @if (p.data_quality_score != null) {
                <div class="mono" style="color:var(--text-faint);font-size:11px;margin-top:6px">
                  Data quality {{ p.data_quality_score }}/100
                </div>
              }
            </div>
          }
        </aside>
      </div>
    </div>
  `,
})
export class ProductDetailComponent {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly route = inject(ActivatedRoute);

  protected readonly ranges: Range[] = ['7d', '30d', '90d', 'all'];

  protected readonly product = signal<ProductResponse | null>(null);
  protected readonly history = signal<PriceHistory | null>(null);
  protected readonly stats = signal<ProductStats | null>(null);
  protected readonly loading = signal(true);
  protected readonly historyLoading = signal(true);
  protected readonly error = signal<ApiError | null>(null);
  protected readonly range = signal<Range>('90d');
  protected readonly inWatchlist = signal(false);
  protected readonly watchlistBusy = signal(false);

  private productId = '';

  protected readonly categoryLabel = computed(() => {
    const p = this.product();
    return p ? (CATEGORY_LABELS[p.category] ?? p.category) : '';
  });

  protected readonly chartLabels = computed(() =>
    (this.history()?.points ?? []).map((pt) =>
      new Date(pt.scraped_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    ),
  );
  protected readonly chartValues = computed(() =>
    (this.history()?.points ?? []).map((pt) => pt.price_usd),
  );

  constructor() {
    this.route.paramMap.subscribe((params) => {
      this.productId = params.get('id') ?? '';
      this.loadAll();
    });
  }

  protected setRange(range: Range): void {
    this.range.set(range);
    this.loadHistory();
  }

  protected addToWatchlist(product: ProductResponse): void {
    if (!this.auth.isAuthenticated()) {
      this.toast.info('Sign in to track this product.');
      return;
    }
    if (this.inWatchlist()) return;
    this.watchlistBusy.set(true);
    this.api.addToWatchlist(product.canonical_product_id, { alert_enabled: true }).subscribe({
      next: () => {
        this.inWatchlist.set(true);
        this.watchlistBusy.set(false);
        this.toast.success(`Tracking "${product.name}".`);
      },
      error: (err: ApiError) => {
        this.watchlistBusy.set(false);
        // 409 = already there — treat as success state.
        if (err.status === 409) {
          this.inWatchlist.set(true);
        } else {
          this.toast.error(err.message);
        }
      },
    });
  }

  private loadAll(): void {
    if (!this.productId) return;
    this.loading.set(true);
    this.error.set(null);

    this.api.getProduct(this.productId).subscribe({
      next: (product) => {
        this.product.set(product);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err);
        this.loading.set(false);
      },
    });

    this.loadHistory();

    this.api.getProductStats(this.productId).subscribe({
      next: (stats) => this.stats.set(stats),
      error: () => this.stats.set(null),
    });
  }

  private loadHistory(): void {
    if (!this.productId) return;
    this.historyLoading.set(true);
    this.api.getPriceHistory(this.productId, { period: this.range() }).subscribe({
      next: (history) => {
        this.history.set(history);
        this.historyLoading.set(false);
      },
      error: () => {
        this.history.set(null);
        this.historyLoading.set(false);
      },
    });
  }
}
