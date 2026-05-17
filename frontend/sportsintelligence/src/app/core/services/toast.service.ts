/**
 * ToastService — transient notifications.
 *
 * Components read the `toasts` signal; ToastComponent renders it. Toasts
 * auto-dismiss after a timeout (browser only — no timers during SSR).
 */
import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';

export type ToastKind = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

const DEFAULT_TTL = 4_000;

@Injectable({ providedIn: 'root' })
export class ToastService {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  private nextId = 1;

  readonly toasts = signal<Toast[]>([]);

  success(message: string, ttl = DEFAULT_TTL): void {
    this.push('success', message, ttl);
  }

  error(message: string, ttl = DEFAULT_TTL): void {
    this.push('error', message, ttl);
  }

  info(message: string, ttl = DEFAULT_TTL): void {
    this.push('info', message, ttl);
  }

  dismiss(id: number): void {
    this.toasts.update((list) => list.filter((t) => t.id !== id));
  }

  private push(kind: ToastKind, message: string, ttl: number): void {
    const id = this.nextId++;
    this.toasts.update((list) => [...list, { id, kind, message }]);
    if (this.isBrowser && ttl > 0) {
      setTimeout(() => this.dismiss(id), ttl);
    }
  }
}
