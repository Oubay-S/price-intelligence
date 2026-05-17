/**
 * WatchlistPageComponent — the user's tracked products.
 *
 * Auth-gated (authGuard). Loads `GET /watchlist`, lets the user drag a
 * target-price slider per item (committed to `PATCH /watchlist/{id}` on
 * release) and remove items (`DELETE /watchlist/{id}`).
 */
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiError, WatchlistItemResponse } from '../../../core/models';
import { ApiService } from '../../../core/services/api.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../../../shared/components/icon/icon';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton';

/** Local view-model: server item + the in-progress target the slider edits. */
interface WatchRow {
  item: WatchlistItemResponse;
  target: number;
}

@Component({
  selector: 'app-watchlist-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, CurrencyPipe, IconComponent, LoadingSkeletonComponent],
  template: `
    <div class="page fade-up">
      <div class="container wl-layout">
        <div class="wl-head">
          <div>
            <h1 class="serif" style="margin:0;font-size:44px;letter-spacing:-.02em;
              font-weight:400">Watchlist</h1>
            <p style="color:var(--text-dim);margin:8px 0 0">
              Set a target price. Get alerted the second any tracked store drops below it.
            </p>
          </div>
          <a class="btn primary" routerLink="/products">
            <app-icon name="plus" [size]="14" /> Add products
          </a>
        </div>

        @if (loading()) {
          <app-loading-skeleton variant="rows" [count]="4" />
        } @else if (error()) {
          <div class="card empty-state">
            <div class="big">Couldn't load your watchlist.</div>
            <div>{{ error()!.message }}</div>
            <button class="btn ghost" style="margin-top:14px" (click)="load()">Retry</button>
          </div>
        } @else {
          <div class="card elev wl-stats">
            <div>
              <div class="lbl">Tracking</div>
              <div class="big">{{ rows().length }}
                <span style="color:var(--text-faint);font-size:16px">products</span></div>
            </div>
            <div>
              <div class="lbl">Potential savings</div>
              <div class="big" style="color:var(--accent)">
                {{ totalSavings() | currency: 'USD' }}
              </div>
            </div>
            <div>
              <div class="lbl">Within reach</div>
              <div class="big">{{ withinReach() }}<span
                style="color:var(--text-faint);font-size:16px">/{{ rows().length }}</span></div>
            </div>
            <div>
              <div class="lbl">Unread alerts</div>
              <div class="big">{{ unreadTotal() }}</div>
            </div>
          </div>

          @if (rows().length === 0) {
            <div class="card empty-state">
              <div class="big">Your watchlist is empty.</div>
              <a class="btn primary" routerLink="/products" style="margin-top:12px">
                Browse catalogue <app-icon name="arrow-r" [size]="14" />
              </a>
            </div>
          } @else {
            <div class="wl-list">
              @for (row of rows(); track row.item.id) {
                <div class="wl-item">
                  <div class="wl-thumb">
                    @if (row.item.product_image_url) {
                      <img [src]="row.item.product_image_url" [alt]="row.item.product_title" />
                    } @else {
                      <app-icon name="grid" [size]="22" />
                    }
                  </div>

                  <div class="wl-info">
                    <div class="ttl">{{ row.item.product_title }}</div>
                    <div class="sub">
                      {{ row.item.site || 'No live listing' }}
                      @if (row.item.current_price != null) {
                        · now {{ row.item.current_price | currency: 'USD' }}
                      }
                    </div>
                    <div class="tags">
                      <span class="pill">
                        <app-icon name="bell" [size]="10" />
                        {{ row.item.alert_enabled ? 'Alerts on' : 'Alerts off' }}
                      </span>
                      @if (row.item.category) {
                        <span class="pill">{{ row.item.category }}</span>
                      }
                    </div>
                  </div>

                  <div class="thr-slider">
                    <div class="row">
                      <span>Target</span>
                      <span style="color:var(--accent)">{{ row.target | currency: 'USD' }}</span>
                    </div>
                    <input type="range"
                      [min]="sliderMin(row)" [max]="sliderMax(row)" step="0.5"
                      [ngModel]="row.target"
                      (ngModelChange)="setTarget(row, $event)"
                      (change)="commitTarget(row)" />
                    <div class="row">
                      <span>{{ sliderMin(row) | currency: 'USD' }}</span>
                      <span>{{ sliderMax(row) | currency: 'USD' }}</span>
                    </div>
                  </div>

                  <div class="wl-cta">
                    <div class="save-bubble">
                      {{ belowCurrent(row)
                        ? ('Save ' + (savingFor(row) | currency: 'USD'))
                        : 'Above current' }}
                    </div>
                    <div class="small">{{ belowCurrent(row) ? 'when target hit' : 'lower the target' }}</div>
                    <div style="display:flex;gap:6px;margin-top:6px">
                      <button class="btn ghost sm" (click)="remove(row)">
                        <app-icon name="x" [size]="12" /> Remove
                      </button>
                      <a class="btn primary sm"
                        [routerLink]="['/products', row.item.canonical_product_id]">
                        <app-icon name="chart" [size]="12" /> History
                      </a>
                    </div>
                  </div>
                </div>
              }
            </div>
          }
        }
      </div>
    </div>
  `,
})
export class WatchlistPageComponent {
  private readonly api = inject(ApiService);
  private readonly toast = inject(ToastService);

  protected readonly rows = signal<WatchRow[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<ApiError | null>(null);
  protected readonly unreadTotal = signal(0);

  protected readonly totalSavings = computed(() =>
    this.rows().reduce((sum, r) => sum + Math.max(0, this.savingFor(r)), 0),
  );
  protected readonly withinReach = computed(
    () => this.rows().filter((r) => this.belowCurrent(r)).length,
  );

  constructor() {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getWatchlist(1, 100).subscribe({
      next: (res) => {
        this.rows.set(res.items.map((item) => ({ item, target: this.initialTarget(item) })));
        this.unreadTotal.set(res.unread_total);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err);
        this.loading.set(false);
      },
    });
  }

  protected setTarget(row: WatchRow, target: number): void {
    this.rows.update((rows) =>
      rows.map((r) => (r.item.id === row.item.id ? { ...r, target } : r)),
    );
  }

  /** Persist the slider value once the user releases it. */
  protected commitTarget(row: WatchRow): void {
    const current = this.rows().find((r) => r.item.id === row.item.id);
    if (!current) return;
    this.api
      .updateWatchlistItem(current.item.canonical_product_id, { target_price: current.target })
      .subscribe({
        next: (updated) => {
          this.rows.update((rows) =>
            rows.map((r) =>
              r.item.id === row.item.id ? { item: updated, target: current.target } : r,
            ),
          );
          this.toast.success('Target price updated.');
        },
        error: (err: ApiError) => this.toast.error(err.message),
      });
  }

  protected remove(row: WatchRow): void {
    this.api.removeFromWatchlist(row.item.canonical_product_id).subscribe({
      next: () => {
        this.rows.update((rows) => rows.filter((r) => r.item.id !== row.item.id));
        this.toast.info('Removed from watchlist.');
      },
      error: (err: ApiError) => this.toast.error(err.message),
    });
  }

  protected sliderMin(row: WatchRow): number {
    return Math.floor(this.refPrice(row) * 0.5);
  }
  protected sliderMax(row: WatchRow): number {
    return Math.ceil(this.refPrice(row) * 1.3);
  }
  protected belowCurrent(row: WatchRow): boolean {
    const current = row.item.current_price;
    return current != null && row.target < current;
  }
  protected savingFor(row: WatchRow): number {
    const current = row.item.current_price ?? row.target;
    return Math.max(0, current - row.target);
  }

  private refPrice(row: WatchRow): number {
    return row.item.current_price ?? row.target ?? 100;
  }

  private initialTarget(item: WatchlistItemResponse): number {
    if (item.target_price != null) return item.target_price;
    if (item.current_price != null) return +(item.current_price * 0.88).toFixed(2);
    return 50;
  }
}
