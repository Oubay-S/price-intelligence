/**
 * LandingPageComponent — the marketing home page.
 *
 * Hero with a product search bar, a live trending-drops grid (real data
 * from `GET /products/trending`), animated stat counters, feature grid and
 * CTA. The stat counters ease in once, in the browser only, via rAF.
 */
import {
  ChangeDetectionStrategy,
  Component,
  PLATFORM_ID,
  afterNextRender,
  inject,
  signal,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import {
  ApiError,
  ProductResponse,
  TrendingProduct,
} from '../../../core/models';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent, IconName } from '../../../shared/components/icon/icon';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { ProductCardComponent } from '../../../shared/components/product-card/product-card';

interface Feature {
  icon: IconName;
  title: string;
  body: string;
}

interface HeroTile {
  cls: string;
  label: string;
  price: string;
  img: string;
}

@Component({
  selector: 'app-landing-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    DecimalPipe,
    FormsModule,
    IconComponent,
    LoadingSkeletonComponent,
    ProductCardComponent,
  ],
  template: `
    <div class="page fade-up">
      <section class="hero">
        <div class="hero-grid"></div>
        <div class="hero-bg"></div>
        <div class="container" style="position:relative">
          <div class="hero-split">
            <div>
              <span class="eyebrow">
                <span class="dot"></span> Live — tracking sports retailers in real time
              </span>
              <h1>
                Never pay full price<br />
                on your <span class="mark">gear</span> again.
              </h1>
              <p class="lede">
                PriceIntelligent scrapes every major sports retailer in real time — gym, team
                sports, running, combat. Find the lowest price on any product and get alerted
                the moment it drops.
              </p>

              <form
                class="search"
                role="search"
                (submit)="submitSearch($event)"
                style="margin-bottom:18px;max-width:460px"
              >
                <app-icon name="search" [size]="16" />
                <input
                  class="input"
                  type="search"
                  name="q"
                  placeholder="Search shoes, watches, gloves, supplements…"
                  aria-label="Search products"
                  [ngModel]="query()"
                  (ngModelChange)="query.set($event)"
                />
              </form>

              <div style="display:flex;gap:10px;margin-bottom:56px;flex-wrap:wrap">
                <a class="btn primary lg" routerLink="/products">
                  Browse catalogue <app-icon name="arrow-r" [size]="16" />
                </a>
                <a class="btn ghost lg" routerLink="/alerts">See live price drops</a>
              </div>
            </div>

            <div class="hero-collage">
              @for (t of heroTiles; track t.cls) {
                <div class="htile" [class]="t.cls">
                  <img [src]="t.img" alt="" class="htile-img" loading="lazy" />
                  <div class="htile-grad"></div>
                  <div class="htile-label"><span class="dot"></span>{{ t.label }}</div>
                  <div class="htile-price">\${{ t.price }}</div>
                </div>
              }
              <div class="hero-live">
                <span class="dot" style="background:var(--accent)"></span>
                <span class="mono">PRICE DROPPED · 3s AGO</span>
              </div>
            </div>
          </div>

          <div class="stats-row">
            <div class="stat">
              <div class="num"><em>{{ counts()[0] | number: '1.0-0' }}</em></div>
              <div class="lbl">Prices tracked</div>
            </div>
            <div class="stat">
              <div class="num"><em>{{ counts()[1] | number: '1.0-0' }}</em></div>
              <div class="lbl">Stores scraped</div>
            </div>
            <div class="stat">
              <div class="num">$<em>{{ counts()[2] | number: '1.1-1' }}</em>M</div>
              <div class="lbl">Saved by users</div>
            </div>
            <div class="stat">
              <div class="num"><em>{{ counts()[3] | number: '1.0-0' }}</em> min</div>
              <div class="lbl">Refresh interval</div>
            </div>
          </div>
        </div>
      </section>

      <section class="container" style="padding-top:64px">
        <div class="page-head">
          <div style="display:flex;align-items:baseline;justify-content:space-between;gap:16px">
            <h1>Trending price drops</h1>
            <a
              routerLink="/products"
              class="mono"
              style="color:var(--accent);font-size:12px;text-decoration:none"
              >View all <app-icon name="arrow-r" [size]="12" /></a>
          </div>
          <p>The biggest live drops across every tracked store in the last 24 hours.</p>
        </div>

        @if (trendingLoading()) {
          <app-loading-skeleton variant="card-grid" [count]="6" />
        } @else if (trendingError()) {
          <div class="card empty-state">
            <div class="big">Couldn't load trending products.</div>
            <div>{{ trendingError()!.message }}</div>
          </div>
        } @else if (trending().length === 0) {
          <div class="card empty-state">
            <div class="big">No trending drops right now.</div>
            <div>Check back soon — prices refresh every 15 minutes.</div>
          </div>
        } @else {
          <div class="cat-grid">
            @for (p of trending(); track p.canonical_product_id) {
              <app-product-card
                [product]="p"
                [inWatchlist]="watchlistIds().has(p.canonical_product_id)"
                (watchlistToggle)="toggleWatchlist($event)"
                (compareSelect)="addToCompare($event)"
              />
            }
          </div>
        }
      </section>

      <section class="container" style="padding-top:72px">
        <div class="features">
          @for (f of features; track f.title) {
            <div class="feature card">
              <div class="icon"><app-icon [name]="f.icon" [size]="18" /></div>
              <h3>{{ f.title }}</h3>
              <p>{{ f.body }}</p>
            </div>
          }
        </div>
      </section>

      <section class="container" style="padding-bottom:100px;padding-top:72px">
        <div class="card elev" style="padding:48px;display:grid;
          grid-template-columns:1fr auto;align-items:center;gap:24px">
          <div>
            <h2 class="serif" style="font-size:44px;margin:0;letter-spacing:-.02em;line-height:1">
              Start tracking in
              <span style="color:var(--accent);font-style:italic">under a minute.</span>
            </h2>
            <p style="color:var(--text-dim);margin:12px 0 0;max-width:520px">
              Free forever — no credit card, no store accounts. Search a product and we'll do
              the rest.
            </p>
          </div>
          <a class="btn primary lg" routerLink="/register">
            Create free account <app-icon name="arrow-r" [size]="16" />
          </a>
        </div>
      </section>
    </div>
  `,
})
export class LandingPageComponent {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  protected readonly query = signal('');

  protected readonly trending = signal<ProductResponse[]>([]);
  protected readonly trendingLoading = signal(true);
  protected readonly trendingError = signal<ApiError | null>(null);
  protected readonly watchlistIds = signal<Set<string>>(new Set());

  private readonly targets = [184293, 428, 2.4, 15];
  protected readonly counts = signal<number[]>(this.targets);

  protected readonly heroTiles: HeroTile[] = [
    {
      cls: 'htile-shoe',
      label: 'Running · −22%',
      price: '142.80',
      img: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80',
    },
    {
      cls: 'htile-watch',
      label: 'GPS Watch',
      price: '489.00',
      img: 'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=500&q=80',
    },
    {
      cls: 'htile-ball',
      label: 'Team · size 5',
      price: '24.99',
      img: 'https://images.unsplash.com/photo-1614632537190-23e4b2e69c88?w=700&q=80',
    },
  ];

  protected readonly features: Feature[] = [
    {
      icon: 'chart',
      title: 'Price history that matters',
      body: '90 days of scraped price data per product — see the real floor, not just today\'s deal.',
    },
    {
      icon: 'compare',
      title: 'Side-by-side comparison',
      body: 'One table, every store. Shipping, stock and delivery window all normalized.',
    },
    {
      icon: 'bell',
      title: 'Threshold alerts',
      body: 'Set a target price on anything in your watchlist. We ping you the second it\'s hit.',
    },
    {
      icon: 'globe',
      title: 'Every store, one place',
      body: 'From big marketplaces to niche sports specialists — if they sell it, we\'re watching.',
    },
    {
      icon: 'zap',
      title: '15-minute refresh',
      body: 'Not a nightly batch. Hot items are rechecked every 15 minutes via the streaming path.',
    },
    {
      icon: 'shield',
      title: 'No affiliate bias',
      body: 'We show the cheapest price. Full stop. No reordered tables or sponsored stores.',
    },
  ];

  constructor() {
    this.loadTrending();
    this.loadWatchlistIds();

    if (this.isBrowser) {
      this.counts.set([0, 0, 0, 0]);
      afterNextRender(() => this.animate());
    }
  }

  protected submitSearch(event: Event): void {
    event.preventDefault();
    const q = this.query().trim();
    if (!q) return;
    this.router.navigate(['/products'], { queryParams: { q } });
  }

  protected toggleWatchlist(product: ProductResponse): void {
    if (!this.auth.isAuthenticated()) {
      this.toast.info('Sign in to build your watchlist.');
      this.router.navigate(['/login'], { queryParams: { returnUrl: '/' } });
      return;
    }
    const id = product.canonical_product_id;
    if (this.watchlistIds().has(id)) {
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

  private loadTrending(): void {
    this.api.getTrending('24h', { limit: 6 }).subscribe({
      next: (res) => {
        this.trending.set(res.products.map((t) => this.toProduct(t)));
        this.trendingLoading.set(false);
      },
      error: (err: ApiError) => {
        this.trendingError.set(err);
        this.trendingLoading.set(false);
      },
    });
  }

  private loadWatchlistIds(): void {
    if (!this.auth.isAuthenticated()) return;
    this.api.getWatchlist(1, 100).subscribe({
      next: (res) =>
        this.watchlistIds.set(new Set(res.items.map((i) => i.canonical_product_id))),
      error: () => {
        /* non-fatal — landing still works without watchlist state */
      },
    });
  }

  private mutateIds(id: string, add: boolean): void {
    const next = new Set(this.watchlistIds());
    add ? next.add(id) : next.delete(id);
    this.watchlistIds.set(next);
  }

  /** Adapt the lean TrendingProduct shape into the ProductResponse the
   *  shared ProductCardComponent expects. */
  private toProduct(t: TrendingProduct): ProductResponse {
    return {
      canonical_product_id: t.canonical_product_id,
      name: t.product_name,
      site: t.best_site,
      listing_url: t.listing_url,
      category: t.category,
      brand_raw: t.brand_raw,
      in_stock: true,
      image_url: t.image_url ?? null,
      pricing: {
        current: t.current_price,
        currency_raw: 'MAD',
        discount_pct: t.drop_pct ?? null,
        trend: t.price_trend,
      },
      ratings:
        t.rating_score != null ? { score: t.rating_score, count: 0 } : null,
      certifications: [],
      tags: t.tags,
      purpose_tags: [],
      brand_tier: t.brand_tier,
      scraped_at: new Date().toISOString(),
    };
  }

  /** Ease the four counters from 0 to their target over ~1.6s. */
  private animate(): void {
    const duration = 1600;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      this.counts.set(this.targets.map((t) => t * eased));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
}
