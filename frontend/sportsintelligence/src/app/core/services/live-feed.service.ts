/**
 * LiveFeedService — the single app-wide subscription to the public
 * `/ws/live-prices` feed.
 *
 * One socket for the whole app: `connectLivePrices()` is shared via
 * `shareReplay` so the navbar status dot, drop toasts and the alerts page
 * all read the same stream instead of each opening their own WebSocket.
 *
 * Exposes:
 *  - `status`        — connection state for the navbar indicator.
 *  - `recentEvents`  — last 10 price events (for a live ticker).
 *  - `events$()`     — the shared message stream for richer consumers.
 *
 * SSR-safe: `start()` is a no-op on the server; the underlying
 * WebSocketService already short-circuits during prerender.
 */
import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';
import { Observable, Subscription } from 'rxjs';
import { shareReplay } from 'rxjs/operators';

import { PriceEventBroadcast, WsMessage, WsStatus } from '../models';
import { ToastService } from './toast.service';
import { WebSocketService } from './websocket.service';

const DROP_TOAST_TTL = 5_000;
const MAX_RECENT = 10;

@Injectable({ providedIn: 'root' })
export class LiveFeedService {
  private readonly ws = inject(WebSocketService);
  private readonly toast = inject(ToastService);
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));

  readonly status = signal<WsStatus>('closed');
  readonly recentEvents = signal<PriceEventBroadcast[]>([]);

  /** Shared hot stream — one socket regardless of subscriber count. */
  private readonly stream$ = this.ws
    .connectLivePrices()
    .pipe(shareReplay({ bufferSize: 1, refCount: false }));

  private started = false;
  private sub: Subscription | null = null;

  /** Open the global connection. Called once from the app shell. */
  start(): void {
    if (this.started || !this.isBrowser) return;
    this.started = true;
    this.sub = this.stream$.subscribe((msg) => this.handle(msg));
  }

  /** Shared message stream for consumers that need raw events. */
  events$(): Observable<WsMessage> {
    return this.stream$;
  }

  private handle(msg: WsMessage): void {
    if (msg.kind === 'status') {
      this.status.set(msg.status);
      return;
    }
    if (msg.kind !== 'price-event') return;

    const e = msg.data;
    this.recentEvents.update((list) => [e, ...list].slice(0, MAX_RECENT));

    // Toast only on an actual drop.
    if (e.price_before != null && e.price_after < e.price_before) {
      const pct = ((e.price_before - e.price_after) / e.price_before) * 100;
      this.toast.info(
        `${e.product_name} dropped ${pct.toFixed(0)}% to ${e.price_after.toFixed(2)} MAD on ${e.site}`,
        DROP_TOAST_TTL,
      );
    }
  }
}
