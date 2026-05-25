/**
 * AnalyticsDashboardComponent — visualises the Data Analyst's outputs.
 *
 * Pulls the seven `/analytics/*` endpoints in parallel and renders them with
 * Chart.js (via the SSR-safe `app-chart`) plus a heatmap table, a discounts
 * table, and recommendation cards. All chart configs are `computed` signals so
 * they rebuild automatically once the data arrives.
 */
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { forkJoin } from 'rxjs';
import { ChartConfiguration } from 'chart.js';

import {
  AnalyticsKpis,
  ApiError,
  CategoryPriceStat,
  HeatmapCell,
  Recommendation,
  StorePriceStat,
  TimeSeriesPoint,
  TopDiscount,
} from '../../../core/models';
import { ApiService } from '../../../core/services/api.service';
import { ChartComponent } from '../../../shared/components/chart/chart';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton';

const STORE_COLORS: Record<string, string> = {
  ebay: '#3b82f6',
  jumia: '#f59e0b',
  'sport-direct': '#10b981',
};

const FALLBACK_COLORS = ['#6366f1', '#ec4899', '#14b8a6', '#f97316', '#8b5cf6', '#ef4444', '#22c55e'];

function colorFor(key: string, i: number): string {
  return STORE_COLORS[key] ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length];
}

@Component({
  selector: 'app-analytics-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe, ChartComponent, LoadingSkeletonComponent],
  template: `
    <div class="page fade-up">
      <div class="container">
        <div class="page-head">
          <h1>Market analytics</h1>
          <p>
            Price intelligence across stores and sports, computed by the data-analysis pipeline.
            @if (generatedAt()) {
              <span class="mono" style="color:var(--text-dim);font-size:12px">
                · snapshot {{ generatedAt() }}
              </span>
            }
          </p>
        </div>

        @if (loading()) {
          <app-loading-skeleton variant="card-grid" [count]="6" />
        } @else if (error()) {
          <div class="card empty-state">
            <div class="big">Couldn't load analytics.</div>
            <div>{{ error()!.message }}</div>
            <button class="btn ghost" style="margin-top:14px" (click)="load()">Retry</button>
          </div>
        } @else {
          <!-- KPI cards -->
          @if (kpis(); as k) {
            <div class="kpi-grid">
              <div class="card kpi"><span>Products</span><strong>{{ k.total_products | number }}</strong></div>
              <div class="card kpi"><span>Stores</span><strong>{{ k.total_stores }}</strong></div>
              <div class="card kpi"><span>Categories</span><strong>{{ k.total_categories }}</strong></div>
              <div class="card kpi"><span>Avg price</span><strong>{{ k.average_price | number: '1.0-0' }} MAD</strong></div>
              <div class="card kpi"><span>Median price</span><strong>{{ k.median_price | number: '1.0-0' }} MAD</strong></div>
              <div class="card kpi"><span>Avg discount</span><strong>{{ k.average_discount | number: '1.0-1' }}%</strong></div>
            </div>
          }

          <!-- Charts -->
          <div class="chart-grid">
            <div class="card chart-card">
              <h3>Price by store</h3>
              <app-chart [config]="storeChart()" />
            </div>
            <div class="card chart-card">
              <h3>Price by category</h3>
              <app-chart [config]="categoryChart()" />
            </div>
            <div class="card chart-card wide">
              <h3>Median price over time</h3>
              <app-chart [config]="timeSeriesChart()" />
            </div>
          </div>

          <!-- Heatmap -->
          <div class="card chart-card" style="margin-top:18px">
            <h3>Median price — store × category</h3>
            <div class="heatmap-scroll">
              <table class="heatmap">
                <thead>
                  <tr>
                    <th></th>
                    @for (c of heatmapCategories(); track c) { <th>{{ c }}</th> }
                  </tr>
                </thead>
                <tbody>
                  @for (s of heatmapStores(); track s) {
                    <tr>
                      <th>{{ s }}</th>
                      @for (c of heatmapCategories(); track c) {
                        <td [style.background]="heatColor(s, c)">{{ heatValue(s, c) }}</td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <!-- Top discounts -->
          <div class="card chart-card" style="margin-top:18px">
            <h3>Top discounts</h3>
            <div class="heatmap-scroll">
              <table class="data-table">
                <thead>
                  <tr><th>Product</th><th>Store</th><th>Category</th><th>Price</th><th>Discount</th></tr>
                </thead>
                <tbody>
                  @for (d of discounts(); track d.name) {
                    <tr>
                      <td>{{ d.name }}</td>
                      <td>{{ d.store }}</td>
                      <td>{{ d.category }}</td>
                      <td class="mono">{{ d.price | number: '1.0-2' }} MAD</td>
                      <td class="mono">−{{ d.discount | number: '1.0-0' }}%</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <!-- Recommendations -->
          @if (recommendations().length) {
            <div class="rec-grid">
              @for (r of recommendations(); track r.recommandation) {
                <div class="card rec-card">
                  <span class="rec-prio" [class.high]="r.priorite === 'Haute'">{{ r.priorite }}</span>
                  <p class="rec-text">{{ r.recommandation }}</p>
                  <p class="rec-just">{{ r.justification }}</p>
                </div>
              }
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [
    `
      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 18px;
      }
      .kpi {
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .kpi span {
        font-size: 12px;
        color: var(--text-dim);
      }
      .kpi strong {
        font-size: 22px;
      }
      .chart-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 18px;
      }
      .chart-card {
        padding: 16px;
      }
      .chart-card h3 {
        margin: 0 0 12px;
        font-size: 14px;
      }
      .chart-card.wide {
        grid-column: 1 / -1;
      }
      .heatmap-scroll {
        overflow-x: auto;
      }
      table.heatmap,
      table.data-table {
        border-collapse: collapse;
        width: 100%;
        font-size: 13px;
      }
      table.heatmap th,
      table.heatmap td {
        padding: 8px 10px;
        text-align: center;
        border: 1px solid var(--line);
        white-space: nowrap;
      }
      table.data-table th,
      table.data-table td {
        padding: 8px 10px;
        text-align: left;
        border-bottom: 1px solid var(--line);
      }
      .rec-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 12px;
        margin-top: 18px;
      }
      .rec-card {
        padding: 14px;
      }
      .rec-prio {
        display: inline-block;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 999px;
        background: var(--line);
        margin-bottom: 8px;
      }
      .rec-prio.high {
        background: #fee2e2;
        color: #b91c1c;
      }
      .rec-text {
        font-weight: 500;
        margin: 0 0 6px;
      }
      .rec-just {
        font-size: 12px;
        color: var(--text-dim);
        margin: 0;
      }
    `,
  ],
})
export class AnalyticsDashboardComponent {
  private readonly api = inject(ApiService);

  protected readonly loading = signal(true);
  protected readonly error = signal<ApiError | null>(null);
  protected readonly generatedAt = signal<string | null>(null);

  protected readonly kpis = signal<AnalyticsKpis | null>(null);
  private readonly stores = signal<StorePriceStat[]>([]);
  private readonly categories = signal<CategoryPriceStat[]>([]);
  private readonly series = signal<TimeSeriesPoint[]>([]);
  private readonly heatmap = signal<HeatmapCell[]>([]);
  protected readonly discounts = signal<TopDiscount[]>([]);
  protected readonly recommendations = signal<Recommendation[]>([]);

  constructor() {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);

    forkJoin({
      kpis: this.api.getAnalyticsKpis(),
      stores: this.api.getPriceByStore(),
      categories: this.api.getPriceByCategory(),
      series: this.api.getPriceTimeSeries(),
      heatmap: this.api.getPriceHeatmap(),
      discounts: this.api.getTopDiscounts(),
      recs: this.api.getRecommendations(),
    }).subscribe({
      next: (res) => {
        this.kpis.set(res.kpis.data);
        this.stores.set(res.stores.data);
        this.categories.set(res.categories.data);
        this.series.set(res.series.data);
        this.heatmap.set(res.heatmap.data);
        this.discounts.set(res.discounts.data);
        this.recommendations.set(res.recs.data);
        this.generatedAt.set(res.kpis.generated_at);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err);
        this.loading.set(false);
      },
    });
  }

  // --- Chart configs -------------------------------------------------------

  protected readonly storeChart = computed<ChartConfiguration<'bar'>>(() => {
    const rows = this.stores();
    return {
      type: 'bar',
      data: {
        labels: rows.map((r) => r.store),
        datasets: [
          { label: 'Average', data: rows.map((r) => r.average_price), backgroundColor: '#3b82f6' },
          { label: 'Median', data: rows.map((r) => r.median_price), backgroundColor: '#93c5fd' },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false },
    };
  });

  protected readonly categoryChart = computed<ChartConfiguration<'bar'>>(() => {
    const rows = this.categories();
    return {
      type: 'bar',
      data: {
        labels: rows.map((r) => r.category),
        datasets: [
          { label: 'Average', data: rows.map((r) => r.average_price), backgroundColor: '#10b981' },
          { label: 'Median', data: rows.map((r) => r.median_price), backgroundColor: '#6ee7b7' },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false },
    };
  });

  protected readonly timeSeriesChart = computed<ChartConfiguration<'line'>>(() => {
    const rows = this.series();
    const dates = [...new Set(rows.map((r) => r.scraped_date))].sort();
    const storeKeys = [...new Set(rows.map((r) => r.store))];
    const datasets = storeKeys.map((store, i) => ({
      label: store,
      data: dates.map(
        (d) => rows.find((r) => r.scraped_date === d && r.store === store)?.median_price ?? null,
      ),
      borderColor: colorFor(store, i),
      backgroundColor: colorFor(store, i),
      spanGaps: true,
      tension: 0.3,
    }));
    return {
      type: 'line',
      data: { labels: dates, datasets },
      options: { responsive: true, maintainAspectRatio: false },
    };
  });

  // --- Heatmap helpers -----------------------------------------------------

  protected readonly heatmapStores = computed(() => [...new Set(this.heatmap().map((c) => c.store))]);
  protected readonly heatmapCategories = computed(() => [
    ...new Set(this.heatmap().map((c) => c.category)),
  ]);

  private cell(store: string, category: string): HeatmapCell | undefined {
    return this.heatmap().find((c) => c.store === store && c.category === category);
  }

  protected heatValue(store: string, category: string): string {
    const v = this.cell(store, category)?.median_price;
    return v === undefined ? '—' : Math.round(v).toString();
  }

  protected heatColor(store: string, category: string): string {
    const cell = this.cell(store, category);
    if (!cell) return 'transparent';
    const prices = this.heatmap().map((c) => c.median_price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const t = max === min ? 0.5 : (cell.median_price - min) / (max - min);
    return `rgba(59, 130, 246, ${(0.12 + t * 0.7).toFixed(2)})`;
  }
}
