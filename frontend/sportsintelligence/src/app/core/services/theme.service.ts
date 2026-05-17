/**
 * ThemeService — drives the design-system CSS custom properties.
 *
 * The global stylesheet keys its palette off `data-*` attributes on
 * <html> (`data-accent`, `data-mode`, `data-density`). This service is
 * the single writer of those attributes and persists the choice to
 * localStorage. SSR-safe — no-ops on the server.
 */
import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';

export type Accent = 'lime' | 'cyan' | 'orange' | 'violet';
export type Mode = 'dark' | 'light';
export type Density = 'comfy' | 'compact';

export interface ThemeState {
  accent: Accent;
  mode: Mode;
  density: Density;
}

const STORAGE_KEY = 'pi_theme';
const DEFAULT: ThemeState = { accent: 'lime', mode: 'dark', density: 'comfy' };

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));

  readonly theme = signal<ThemeState>(DEFAULT);

  /** Call once on app start (browser only) to load + apply the saved theme. */
  init(): void {
    if (!this.isBrowser) return;
    const saved = this.read();
    this.theme.set(saved);
    this.apply(saved);
  }

  setAccent(accent: Accent): void {
    this.patch({ accent });
  }

  setMode(mode: Mode): void {
    this.patch({ mode });
  }

  toggleMode(): void {
    this.patch({ mode: this.theme().mode === 'dark' ? 'light' : 'dark' });
  }

  setDensity(density: Density): void {
    this.patch({ density });
  }

  private patch(part: Partial<ThemeState>): void {
    const next = { ...this.theme(), ...part };
    this.theme.set(next);
    this.apply(next);
    this.write(next);
  }

  private apply(t: ThemeState): void {
    if (!this.isBrowser) return;
    const root = document.documentElement;
    root.setAttribute('data-accent', t.accent);
    root.setAttribute('data-mode', t.mode);
    root.setAttribute('data-density', t.density);
  }

  private read(): ThemeState {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? { ...DEFAULT, ...JSON.parse(raw) } : DEFAULT;
    } catch {
      return DEFAULT;
    }
  }

  private write(t: ThemeState): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
    } catch {
      /* storage unavailable — non-fatal */
    }
  }
}
