/**
 * ProductCatalogComponent — the browse/search page.
 *
 * Loads a page of products from `GET /products` (or `GET /products/search`
 * when a query is typed). Category, site, price range, and sort are all
 * server-side — every filter change triggers a reload against the backend,
 * so pagination and ordering span the whole result set, not just one page.
 */
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import {
  ApiError,
  CATEGORY_LABELS,
  PaginatedProducts,
  ProductResponse,
  SORT_LABELS,
  SORT_OPTIONS,
  SUPPLEMENT_CATEGORIES,
  SortOption,
  SupplementCategory,
} from '../../../core/models';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../../../shared/components/icon/icon';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { ProductCardComponent } from '../../../shared/components/product-card/product-card';

const PAGE_SIZE = 24;

@Component({
  selector: 'app-product-catalog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    DecimalPipe,
    IconComponent,
    LoadingSkeletonComponent,
    ProductCardComponent,
  ],
  template: `
    <div class="page fade-up">
      <div class="container cat-layout">
        <!-- Sidebar -->
        <aside class="cat-filters card">
          <div style="padding:14px 16px;border-bottom:1px solid var(--line);
            display:flex;align-items:center;gap:8px;font-weight:500">
            <app-icon name="grid" [size]="14" /> Categories
          </div>
          <div style="padding:10px 8px">
            <div class="cat-tree">
              <button class="cat-tree-all" [class.active]="!category()" (click)="pickCategory(null)">
                <app-icon name="grid" [size]="13" /> All products
              </button>
              @for (c of categories; track c.id) {
                <button class="cat-tree-cat" [class.active]="category() === c.id"
                  (click)="pickCategory(c.id)">
                  <span>{{ c.label }}</span>
                </button>
              }
            </div>
          </div>
          <div class="filter-block">
            <h5>Stores</h5>
            <div style="display:flex;flex-direction:column;gap:9px">
              @for (s of sites; track s.id) {
                <label
                  style="display:flex;align-items:center;gap:9px;font-size:13px;cursor:pointer"
                >
                  <input
                    type="checkbox"
                    [checked]="selectedSites().has(s.id)"
                    (change)="toggleSite(s.id)"
                  />
                  <span>{{ s.label }}</span>
                </label>
              }
            </div>
          </div>
          <div class="filter-block">
            <h5>Price range</h5>
            <div class="mono" style="font-size:12px;color:var(--text-dim);
              display:flex;justify-content:space-between;margin-bottom:8px">
              <span>\${{ priceMin() }}</span><span>\${{ priceMax() }}+</span>
            </div>
            <div style="display:flex;gap:8px">
              <input type="number" class="input" [ngModel]="priceMin()"
                (ngModelChange)="priceMin.set(+$event); onPriceChange()"
                style="padding:7px;font-size:13px" />
              <input type="number" class="input" [ngModel]="priceMax()"
                (ngModelChange)="priceMax.set(+$event); onPriceChange()"
                style="padding:7px;font-size:13px" />
            </div>
          </div>
        </aside>

        <!-- Main -->
        <div>
          <div class="page-head">
            <div style="display:flex;align-items:baseline;justify-content:space-between;gap:16px">
              <h1>{{ heading() }}</h1>
              @if (data(); as d) {
                <span class="mono" style="color:var(--text-dim);font-size:12px">
                  {{ visible().length }} of {{ d.total_count | number }} products
                </span>
              }
            </div>
            <p>Lowest live prices scraped from every tracked store. Refreshed every 15 minutes.</p>
          </div>

          <div class="cat-toolbar">
            <div class="search" style="flex:1">
              <app-icon name="search" [size]="15" />
              <input class="input" placeholder="Search shoes, watches, gloves, supplements…"
                [ngModel]="query()" (ngModelChange)="onSearch($event)" />
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <app-icon name="sort" [size]="14" />
              <select class="select" style="width:190px" [ngModel]="sort()"
                (ngModelChange)="changeSort($event)">
                @for (s of sortOptions; track s) {
                  <option [value]="s">{{ sortLabels[s] }}</option>
                }
              </select>
            </div>
          </div>

          @if (loading()) {
            <app-loading-skeleton variant="card-grid" [count]="9" />
          } @else if (error()) {
            <div class="card empty-state">
              <div class="big">Couldn't load the catalogue.</div>
              <div>{{ error()!.message }}</div>
              <button class="btn ghost" style="margin-top:14px" (click)="load()">Retry</button>
            </div>
          } @else if (visible().length === 0) {
            <div class="card empty-state">
              <div class="big">No products match.</div>
              <div>Try a different category, search term, or price range.</div>
            </div>
          } @else {
            <div class="cat-grid">
              @for (p of visible(); track p.canonical_product_id) {
                <app-product-card
                  [product]="p"
                  [inWatchlist]="watchlistIds().has(p.canonical_product_id)"
                  (watchlistToggle)="toggleWatchlist($event)"
                  (compareSelect)="addToCompare($event)"
                />
              }
            </div>

            @if (data(); as d) {
              @if (d.total_pages > 1) {
                <div class="pagination">
                  <button class="btn ghost sm" [disabled]="!d.has_prev" (click)="goToPage(d.page - 1)">
                    <app-icon name="arrow-r" [size]="12" /> Prev
                  </button>
                  <span class="mono" style="font-size:13px;color:var(--text-dim)">
                    Page {{ d.page }} / {{ d.total_pages }}
                  </span>
                  <button class="btn ghost sm" [disabled]="!d.has_next" (click)="goToPage(d.page + 1)">
                    Next <app-icon name="arrow-r" [size]="12" />
                  </button>
                </div>
              }
            }
          }
        </div>
      </div>
    </div>
  `,
})
export class ProductCatalogComponent {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly categories = SUPPLEMENT_CATEGORIES.map((id) => ({
    id,
    label: CATEGORY_LABELS[id],
  }));
  protected readonly sortOptions = SORT_OPTIONS;
  protected readonly sortLabels = SORT_LABELS;
  protected readonly sites = [
    { id: 'ebay', label: 'eBay' },
    { id: 'sport-direct', label: 'Sport-Direct' },
    { id: 'jumia', label: 'Jumia' },
  ];

  protected readonly data = signal<PaginatedProducts | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<ApiError | null>(null);
  protected readonly watchlistIds = signal<Set<string>>(new Set());

  protected readonly category = signal<SupplementCategory | null>(null);
  protected readonly selectedSites = signal<Set<string>>(new Set());
  protected readonly query = signal('');
  protected readonly sort = signal<SortOption>('scraped_at_desc');
  protected readonly page = signal(1);
  protected readonly priceMin = signal(0);
  protected readonly priceMax = signal(2000);

  private readonly searchInput = new Subject<string>();
  private readonly priceInput = new Subject<void>();

  /** Items as returned by the backend — filtering, sorting and pagination
   *  all happen server-side, so no client-side post-processing is needed. */
  protected readonly visible = computed(() => this.data()?.items ?? []);

  protected readonly heading = computed(() => {
    if (this.query()) return `Results for "${this.query()}"`;
    const cat = this.category();
    return cat ? CATEGORY_LABELS[cat] : 'Sports catalogue';
  });

  constructor() {
    this.searchInput
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe((q) => {
        this.query.set(q);
        this.page.set(1);
        this.load();
      });

    this.priceInput.pipe(debounceTime(400)).subscribe(() => {
      this.page.set(1);
      this.load();
    });

    // React to ?q= from the navbar search (and direct links). Fires once on
    // init too, which performs the first load.
    this.route.queryParamMap.subscribe((params) => {
      this.query.set(params.get('q') ?? '');
      this.page.set(1);
      this.load();
    });

    this.loadWatchlistIds();
  }

  protected onSearch(value: string): void {
    this.searchInput.next(value);
  }

  protected onPriceChange(): void {
    this.priceInput.next();
  }

  protected changeSort(value: SortOption): void {
    this.sort.set(value);
    this.page.set(1);
    this.load();
  }

  protected pickCategory(id: SupplementCategory | null): void {
    this.category.set(id);
    this.page.set(1);
    this.load();
  }

  protected toggleSite(id: string): void {
    const next = new Set(this.selectedSites());
    next.has(id) ? next.delete(id) : next.add(id);
    this.selectedSites.set(next);
    this.page.set(1);
    this.load();
  }

  protected goToPage(page: number): void {
    this.page.set(page);
    this.load();
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);

    const q = this.query().trim();
    const sites = this.selectedSites().size ? [...this.selectedSites()] : undefined;
    const lo = this.priceMin();
    const hi = this.priceMax();
    const common = {
      page: this.page(),
      limit: PAGE_SIZE,
      category: this.category() ?? undefined,
      site: sites,
      min_price: lo > 0 ? lo : undefined,
      // priceMax renders as "$N+", i.e. the slider ceiling means "no upper cap".
      max_price: hi > 0 && hi < 2000 ? hi : undefined,
      sort: this.sort(),
    };
    const request = q
      ? this.api.searchProducts(q, common)
      : this.api.getProducts(common);

    request.subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err);
        this.loading.set(false);
      },
    });
  }

  protected toggleWatchlist(product: ProductResponse): void {
    if (!this.auth.isAuthenticated()) {
      this.toast.info('Sign in to build your watchlist.');
      this.router.navigate(['/login'], { queryParams: { returnUrl: '/products' } });
      return;
    }
    const id = product.canonical_product_id;
    const ids = this.watchlistIds();
    if (ids.has(id)) {
      this.api.removeFromWatchlist(id).subscribe({
        next: () => {
          this.mutateIds(id, false);
          this.toast.info('Removed from watchlist.');
        },
        error: (err: ApiError) => this.toast.error(err.message),
      });
    } else {
      this.api.addToWatchlist(id, { alert_enabled: true }).subscribe({
        next: () => {
          this.mutateIds(id, true);
          this.toast.success(`Tracking "${product.name}".`);
        },
        error: (err: ApiError) => this.toast.error(err.message),
      });
    }
  }

  protected addToCompare(product: ProductResponse): void {
    this.router.navigate(['/compare'], {
      queryParams: { ids: product.canonical_product_id },
    });
  }

  private loadWatchlistIds(): void {
    if (!this.auth.isAuthenticated()) return;
    this.api.getWatchlist(1, 100).subscribe({
      next: (res) => this.watchlistIds.set(new Set(res.items.map((i) => i.canonical_product_id))),
      error: () => {
        /* non-fatal — the catalogue still works without watchlist state */
      },
    });
  }

  private mutateIds(id: string, add: boolean): void {
    const next = new Set(this.watchlistIds());
    add ? next.add(id) : next.delete(id);
    this.watchlistIds.set(next);
  }
}
