/**
 * WebSocketService — live feeds from the FastAPI backend.
 *
 * Backend channels:
 *  - `/ws/live-prices`        — public global price-event feed.
 *  - `/ws/alerts/{userId}`    — per-user alert feed; the access JWT is
 *                               passed as a `?token=` query param because
 *                               browsers can't set headers on a WS handshake.
 *
 * Each `connect*` call returns a cold Observable<WsMessage>. The socket
 * opens on first subscribe and closes on last unsubscribe. A capped
 * exponential backoff reconnects dropped sockets automatically.
 *
 * SSR-safe: on the server, the Observables complete immediately with a
 * single `{ kind: 'status', status: 'closed' }` so nothing tries to open
 * a WebSocket during prerender.
 */
import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { PriceDropAlert, PriceEventBroadcast, WsMessage } from '../models';
import { AuthService } from './auth.service';

const MAX_RETRY_DELAY = 30_000;
const BASE_RETRY_DELAY = 1_000;

@Injectable({ providedIn: 'root' })
export class WebSocketService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly auth = inject(AuthService);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  /** Public global price-event feed. */
  connectLivePrices(): Observable<WsMessage> {
    return this.channel(`${this.wsOrigin()}/ws/live-prices`, 'price-event');
  }

  /** Per-user alert feed. Requires a logged-in user with an access token. */
  connectUserAlerts(userId: string): Observable<WsMessage> {
    const token = this.auth.getAccessToken() ?? '';
    const url = `${this.wsOrigin()}/ws/alerts/${encodeURIComponent(userId)}?token=${encodeURIComponent(token)}`;
    return this.channel(url, 'alert');
  }

  // ---------------------------------------------------------------------------

  /** Build a reconnecting WebSocket Observable for one URL. */
  private channel(url: string, payloadKind: 'price-event' | 'alert'): Observable<WsMessage> {
    return new Observable<WsMessage>((subscriber) => {
      if (!this.isBrowser) {
        subscriber.next({ kind: 'status', status: 'closed' });
        subscriber.complete();
        return;
      }

      let socket: WebSocket | null = null;
      let retries = 0;
      let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
      let closedByClient = false;

      const open = () => {
        subscriber.next({ kind: 'status', status: 'connecting' });
        socket = new WebSocket(url);

        socket.onopen = () => {
          retries = 0;
          subscriber.next({ kind: 'status', status: 'open' });
        };

        socket.onmessage = (event) => {
          subscriber.next(this.parse(event.data, payloadKind));
        };

        socket.onerror = () => {
          subscriber.next({ kind: 'status', status: 'error' });
        };

        socket.onclose = () => {
          subscriber.next({ kind: 'status', status: 'closed' });
          if (closedByClient) return;
          const delay = Math.min(BASE_RETRY_DELAY * 2 ** retries, MAX_RETRY_DELAY);
          retries += 1;
          reconnectTimer = setTimeout(open, delay);
        };
      };

      open();

      // Teardown on unsubscribe.
      return () => {
        closedByClient = true;
        if (reconnectTimer) clearTimeout(reconnectTimer);
        if (socket && socket.readyState <= WebSocket.OPEN) socket.close();
      };
    });
  }

  /** Parse an inbound text frame into a typed WsMessage. */
  private parse(raw: unknown, payloadKind: 'price-event' | 'alert'): WsMessage {
    if (typeof raw !== 'string') {
      return { kind: 'raw', data: raw };
    }
    try {
      const data = JSON.parse(raw);
      if (payloadKind === 'alert') {
        return { kind: 'alert', data: data as PriceDropAlert };
      }
      return { kind: 'price-event', data: data as PriceEventBroadcast };
    } catch {
      return { kind: 'raw', data: raw };
    }
  }

  /** Resolve the WebSocket origin: explicit dev value, else derive from
   *  the page origin so prod works behind the reverse proxy. */
  private wsOrigin(): string {
    if (environment.wsBaseUrl) return environment.wsBaseUrl;
    if (!this.isBrowser) return '';
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}`;
  }
}
