/**
 * AlertsPageComponent — price-drop feed, live + historical.
 *
 *  - Historical: `GET /prices/drops` seeds the feed on load.
 *  - Live: the `/ws/live-prices` WebSocket prepends price events as they
 *    arrive. A toggle pauses/resumes the live stream.
 *
 * SSR-safe: the WebSocket subscription only does work in the browser
 * (see WebSocketService).
 */
import { ChangeDetectionStrategy, Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import { ApiError, PriceDropAlert, WsStatus } from '../../../core/models';
import { ApiService } from '../../../core/services/api.service';
import { LiveFeedService } from '../../../core/services/live-feed.service';
import { IconComponent } from '../../../shared/components/icon/icon';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton';

@Component({
  selector: 'app-alerts-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    CurrencyPipe,
    DatePipe,
    DecimalPipe,
    IconComponent,
    LoadingSkeletonComponent,
  ],
  template: `
    <div class="page fade-up">
      <div class="container alerts-layout">
        <div class="page-head">
          <h1>Price drops</h1>
          <p>Every significant drop our pipeline detects — refreshed live as new scrapes land.</p>
        </div>

        <div class="range-tabs" style="margin-bottom:14px">
          <span style="color:var(--text-dim);font-size:13px;margin-right:6px">Min drop</span>
          @for (t of thresholds; track t) {
            <button [attr.aria-pressed]="threshold() === t" (click)="setThreshold(t)">
              {{ t }}%+
            </button>
          }
        </div>

        <div class="live-banner">
          <span class="dot" [class.on]="wsStatus() === 'open'" [class.off]="wsStatus() !== 'open'"></span>
          <span>{{ statusLabel() }}</span>
          <button class="btn ghost sm" style="margin-left:auto" (click)="toggleLive()">
            {{ liveOn() ? 'Pause live feed' : 'Resume live feed' }}
          </button>
        </div>

        @if (loading()) {
          <app-loading-skeleton variant="rows" [count]="6" />
        } @else if (error()) {
          <div class="card empty-state">
            <div class="big">Couldn't load price drops.</div>
            <div>{{ error()!.message }}</div>
            <button class="btn ghost" style="margin-top:14px" (click)="load()">Retry</button>
          </div>
        } @else if (feed().length === 0) {
          <div class="card empty-state">
            <div class="big">No price drops yet.</div>
            <div>New drops will appear here the moment the pipeline detects one.</div>
          </div>
        } @else {
          <div class="alert-feed">
            @for (a of feed(); track $index) {
              <div class="alert-row" [class.unread]="a.live">
                <div class="thumb">
                  @if (a.image_url) {
                    <img [src]="a.image_url" [alt]="a.product_name" />
                  } @else {
                    <app-icon name="tag" [size]="20" />
                  }
                </div>
                <div>
                  <a class="ttl" [routerLink]="['/products', a.canonical_product_id]">
                    {{ a.product_name }}
                  </a>
                  <div class="meta">
                    {{ a.site }} ·
                    {{ a.price_before | currency: 'MAD' }} →
                    {{ a.price_after | currency: 'MAD' }}
                    · {{ a.detected_at | date: 'short' }}
                    @if (a.live) { · <span style="color:var(--accent)">live</span> }
                  </div>
                </div>
                <div class="drop">
                  <div class="pct">−{{ a.drop_pct | number: '1.0-1' }}%</div>
                  <div class="now">{{ a.price_after | currency: 'MAD' }}</div>
                </div>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class AlertsPageComponent implements OnDestroy {
  private readonly api = inject(ApiService);
  private readonly liveFeed = inject(LiveFeedService);

  protected readonly drops = signal<PriceDropAlert[]>([]);
  protected readonly liveEvents = signal<(PriceDropAlert & { live: true })[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<ApiError | null>(null);
  protected readonly wsStatus = signal<WsStatus>('closed');
  protected readonly liveOn = signal(true);

  protected readonly thresholds = [5, 10, 20, 30];
  protected readonly threshold = signal(10);

  /** Live events first, then the historical drops. */
  protected readonly feed = computed(() => [
    ...this.liveEvents(),
    ...this.drops().map((d) => ({ ...d, live: false as const })),
  ]);

  protected readonly statusLabel = computed(() => {
    if (!this.liveOn()) return 'Live feed paused';
    switch (this.wsStatus()) {
      case 'open': return 'Live — connected to the price stream';
      case 'connecting': return 'Connecting to the live price stream…';
      case 'error': return 'Live stream error — retrying';
      default: return 'Live stream offline';
    }
  });

  private wsSub: Subscription | null = null;

  constructor() {
    this.load();
    this.startLive();
  }

  protected setThreshold(t: number): void {
    if (this.threshold() === t) return;
    this.threshold.set(t);
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getPriceDrops({ threshold: this.threshold(), limit: 30 }).subscribe({
      next: (res) => {
        // Sort historical drops by drop percentage, largest first.
        this.drops.set([...res.alerts].sort((a, b) => b.drop_pct - a.drop_pct));
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err);
        this.loading.set(false);
      },
    });
  }

  protected toggleLive(): void {
    if (this.liveOn()) {
      this.stopLive();
      this.liveOn.set(false);
    } else {
      this.liveOn.set(true);
      this.startLive();
    }
  }

  private startLive(): void {
    this.wsSub = this.liveFeed.events$().subscribe((msg) => {
      if (msg.kind === 'status') {
        this.wsStatus.set(msg.status);
      } else if (msg.kind === 'price-event') {
        const e = msg.data;
        // Only surface actual drops (price_after below price_before).
        if (e.price_before != null && e.price_after < e.price_before) {
          const drop: PriceDropAlert & { live: true } = {
            canonical_product_id: e.canonical_product_id,
            product_name: e.product_name,
            image_url: null,
            site: e.site,
            listing_url: '',
            category: 'strength_home_gym',
            price_before: e.price_before,
            price_after: e.price_after,
            currency: e.currency,
            drop_pct:
              e.drop_pct ?? ((e.price_before - e.price_after) / e.price_before) * 100,
            alert_type: 'price_drop',
            scraped_at: e.scraped_at,
            detected_at: new Date().toISOString(),
            live: true,
          };
          // Keep the live list bounded to the 20 most recent.
          this.liveEvents.update((list) => [drop, ...list].slice(0, 20));
        }
      }
    });
  }

  private stopLive(): void {
    this.wsSub?.unsubscribe();
    this.wsSub = null;
    this.wsStatus.set('closed');
  }

  ngOnDestroy(): void {
    this.stopLive();
  }
}
