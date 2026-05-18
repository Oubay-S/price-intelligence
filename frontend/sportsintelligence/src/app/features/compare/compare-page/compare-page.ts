/**
 * ComparePageComponent — cross-store price comparison.
 *
 * The user picks up to 4 products (via search); the page calls
 * `GET /prices/compare?product_ids=...` and renders one table per product,
 * rows sorted by landed cost (price + shipping), cheapest highlighted.
 *
 * Pre-selectable via `?ids=A,B` query params (used by the detail page's
 * "Compare across stores" button).
 */
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs/operators';

import {
  ApiError,
  ProductComparison,
  SearchResult,
  SitePriceSnapshot,
} from '../../../core/models';
import { ApiService } from '../../../core/services/api.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../../../shared/components/icon/icon';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton';

const MAX_PRODUCTS = 4;

@Component({
  selector: 'app-compare-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    CurrencyPipe,
    DatePipe,
    DecimalPipe,
    IconComponent,
    LoadingSkeletonComponent,
  ],
  template: `
    <div class="page fade-up">
      <div class="container cmp-layout">
        <div class="page-head">
          <h1>Compare prices</h1>
          <p>Add up to {{ maxProducts }} products and see every store side by side — price,
            shipping and stock all normalized.</p>
        </div>

        <!-- Search to add a product -->
        <div class="search" style="margin-bottom:14px;position:relative">
          <app-icon name="search" [size]="16" />
          <input class="input" placeholder="Search a product to add to the comparison…"
            [ngModel]="query()" (ngModelChange)="onSearch($event)"
            (focus)="dropdownOpen.set(true)" (blur)="closeDropdownSoon()" />
          @if (dropdownOpen() && results().length) {
            <div class="gs-dropdown">
              @for (r of results(); track r.canonical_product_id) {
                <button class="gs-row" (mousedown)="addProduct(r)">
                  <span class="gs-row-thumb">
                    @if (r.image_url) { <img [src]="r.image_url" alt="" /> }
                  </span>
                  <div class="gs-row-body">
                    <div class="gs-row-name">{{ r.product_name }}</div>
                    <div class="gs-row-sub">{{ r.brand_raw }} · {{ r.best_site }}</div>
                  </div>
                  <div class="gs-row-price mono">{{ r.current_price | currency: 'MAD' }}</div>
                </button>
              }
            </div>
          }
        </div>

        <!-- Selected chips -->
        @if (selectedIds().length) {
          <div class="cmp-add-row">
            @for (id of selectedIds(); track id) {
              <span class="cmp-chip">
                {{ labelFor(id) }}
                <button type="button" class="btn quiet sm" style="padding:0"
                  (click)="removeProduct(id)" aria-label="Remove">
                  <app-icon name="x" [size]="12" />
                </button>
              </span>
            }
            <button class="btn quiet sm" (click)="clearAll()">Clear all</button>
          </div>
        }

        @if (loading()) {
          <app-loading-skeleton variant="block" height="260px" />
        } @else if (error()) {
          <div class="card empty-state">
            <div class="big">Comparison failed.</div>
            <div>{{ error()!.message }}</div>
          </div>
        } @else if (!selectedIds().length) {
          <div class="card empty-state">
            <div class="big">Nothing to compare yet.</div>
            <div>Search above to add your first product.</div>
          </div>
        } @else {
          @for (cmp of comparisons(); track cmp.canonical_product_id) {
            <div class="card" style="margin-bottom:18px">
              <div style="padding:16px 20px;display:flex;align-items:center;
                justify-content:space-between;border-bottom:1px solid var(--line);
                gap:16px;flex-wrap:wrap">
                <div>
                  <div style="font-weight:500">{{ cmp.product_name }}</div>
                  <div style="font-size:12px;color:var(--text-dim);margin-top:3px">
                    {{ cmp.sites_prices.length }} stores ·
                    price gap {{ cmp.price_gap_pct | number: '1.0-1' }}%
                  </div>
                </div>
                <span class="pill accent">
                  <app-icon name="zap" [size]="11" /> Best: {{ cmp.best_site }}
                </span>
              </div>
              <div class="scroll-x">
                <table class="cmp-table">
                  <thead>
                    <tr>
                      <th style="width:26%">Store</th>
                      <th>Price</th>
                      <th>Shipping</th>
                      <th>Landed cost</th>
                      <th>Stock</th>
                      <th>Last seen</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (row of sortedRows(cmp); track row.site; let i = $index) {
                      <tr [class.best]="i === 0">
                        <td>
                          <div class="store">
                            <span class="store-logo">{{ row.site.charAt(0).toUpperCase() }}</span>
                            <div>
                              <div>{{ row.site }}</div>
                            </div>
                            @if (i === 0) {
                              <span class="pill accent" style="margin-left:6px">
                                <app-icon name="zap" [size]="10" /> Best
                              </span>
                            }
                          </div>
                        </td>
                        <td><span class="cmp-price">{{ row.price_usd | currency: 'MAD' }}</span></td>
                        <td class="mono" [style.color]="
                          (row.shipping_cost ?? 0) === 0 ? 'var(--success)' : 'var(--text-dim)'">
                          {{ (row.shipping_cost ?? 0) === 0
                            ? 'Free' : (row.shipping_cost | currency: 'MAD') }}
                        </td>
                        <td class="mono" style="font-weight:500">
                          {{ landed(row) | currency: 'MAD' }}
                        </td>
                        <td>
                          @if (row.in_stock) {
                            <span class="pill success"><span class="dot"></span> In stock</span>
                          } @else {
                            <span class="pill danger"><span class="dot"></span> Out of stock</span>
                          }
                        </td>
                        <td style="color:var(--text-dim)" class="mono">
                          {{ row.last_seen | date: 'short' }}
                        </td>
                        <td>
                          <a class="btn ghost sm" [href]="row.listing_url" target="_blank"
                            rel="noopener">Visit <app-icon name="arrow-r" [size]="12" /></a>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }
        }
      </div>
    </div>
  `,
})
export class ComparePageComponent {
  private readonly api = inject(ApiService);
  private readonly toast = inject(ToastService);
  private readonly route = inject(ActivatedRoute);

  protected readonly maxProducts = MAX_PRODUCTS;

  protected readonly selectedIds = signal<string[]>([]);
  protected readonly comparisons = signal<ProductComparison[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<ApiError | null>(null);

  protected readonly query = signal('');
  protected readonly results = signal<SearchResult[]>([]);
  protected readonly dropdownOpen = signal(false);

  /** name lookup for the selected chips, keyed by product id. */
  private readonly names = signal<Record<string, string>>({});

  private readonly searchInput = new Subject<string>();

  protected readonly labelCount = computed(() => this.selectedIds().length);

  constructor() {
    this.searchInput
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) =>
          q.trim() ? this.api.searchProducts(q.trim(), { limit: 6 }) : Promise.resolve(null),
        ),
      )
      .subscribe((res) => {
        // searchProducts returns PaginatedProducts; map to lightweight rows.
        const items = res?.items ?? [];
        this.results.set(
          items.map((p) => ({
            canonical_product_id: p.canonical_product_id,
            product_name: p.name,
            brand_raw: p.brand_raw,
            category: p.category,
            image_url: p.image_url,
            current_price: p.pricing.current,
            discount_pct: p.pricing.discount_pct,
            price_trend: p.pricing.trend,
            rating_score: p.ratings?.score,
            best_site: p.site,
            listing_url: p.listing_url,
            tags: p.tags,
          })),
        );
      });

    // Pre-select from ?ids=A,B
    const ids = this.route.snapshot.queryParamMap.get('ids');
    if (ids) {
      this.selectedIds.set(ids.split(',').filter(Boolean).slice(0, MAX_PRODUCTS));
      this.loadComparison();
    }
  }

  protected onSearch(value: string): void {
    this.query.set(value);
    this.searchInput.next(value);
  }

  protected closeDropdownSoon(): void {
    setTimeout(() => this.dropdownOpen.set(false), 160);
  }

  protected addProduct(r: SearchResult): void {
    if (this.selectedIds().includes(r.canonical_product_id)) return;
    if (this.selectedIds().length >= MAX_PRODUCTS) {
      this.toast.info(`You can compare up to ${MAX_PRODUCTS} products.`);
      return;
    }
    this.names.update((n) => ({ ...n, [r.canonical_product_id]: r.product_name }));
    this.selectedIds.update((ids) => [...ids, r.canonical_product_id]);
    this.query.set('');
    this.results.set([]);
    this.loadComparison();
  }

  protected removeProduct(id: string): void {
    this.selectedIds.update((ids) => ids.filter((x) => x !== id));
    this.loadComparison();
  }

  protected clearAll(): void {
    this.selectedIds.set([]);
    this.comparisons.set([]);
  }

  protected labelFor(id: string): string {
    return this.names()[id] ?? id;
  }

  protected landed(row: SitePriceSnapshot): number {
    return row.landed_cost ?? row.price_usd + (row.shipping_cost ?? 0);
  }

  protected sortedRows(cmp: ProductComparison): SitePriceSnapshot[] {
    return [...cmp.sites_prices].sort((a, b) => this.landed(a) - this.landed(b));
  }

  private loadComparison(): void {
    const ids = this.selectedIds();
    if (!ids.length) {
      this.comparisons.set([]);
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.api.comparePrices(ids).subscribe({
      next: (res) => {
        this.comparisons.set(res.products);
        // Backfill chip names from the comparison payload.
        const names = { ...this.names() };
        for (const p of res.products) names[p.canonical_product_id] = p.product_name;
        this.names.set(names);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err);
        this.loading.set(false);
      },
    });
  }
}
