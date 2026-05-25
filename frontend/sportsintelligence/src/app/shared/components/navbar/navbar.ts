/**
 * NavbarComponent — sticky top navigation.
 *
 * Renders the brand, primary nav links, theme (dark/light) toggle, and an
 * auth-aware right side: signed-out shows Sign in / Get started; signed-in
 * shows the alerts bell and a user-menu dropdown with logout.
 */
import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import { LiveFeedService } from '../../../core/services/live-feed.service';
import { ThemeService } from '../../../core/services/theme.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../icon/icon';

@Component({
  selector: 'app-navbar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, IconComponent, FormsModule],
  template: `
    <header class="header">
      <a routerLink="/" class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <span class="brand-name">Price<em>Intelligent</em></span>
      </a>

      <nav class="nav">
        <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Home</a>
        <a routerLink="/products" routerLinkActive="active">Catalogue</a>
        <a routerLink="/compare" routerLinkActive="active">Compare</a>
        <a routerLink="/analytics" routerLinkActive="active">Analytics</a>
        <a routerLink="/alerts" routerLinkActive="active">Price drops</a>
        @if (auth.isAuthenticated()) {
          <a routerLink="/watchlist" routerLinkActive="active">Watchlist</a>
        }
      </nav>

      <form class="search nav-search" role="search" (submit)="submitSearch($event)">
        <app-icon name="search" [size]="15" />
        <input
          class="input"
          type="search"
          name="q"
          placeholder="Search products…"
          aria-label="Search products"
          [ngModel]="searchTerm()"
          (ngModelChange)="searchTerm.set($event)"
        />
      </form>

      <div class="header-right">
        <span
          class="ws-dot"
          [style.background]="wsDotColor()"
          [title]="wsDotTitle()"
          aria-hidden="true"
          style="width:8px;height:8px;border-radius:50%;display:inline-block;flex:none"
        ></span>

        <button
          type="button"
          class="btn quiet"
          (click)="theme.toggleMode()"
          [attr.aria-label]="theme.theme().mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
        >
          <app-icon [name]="theme.theme().mode === 'dark' ? 'sun' : 'moon'" [size]="16" />
        </button>

        @if (auth.isAuthenticated()) {
          <a class="btn quiet" routerLink="/alerts" title="Price drop alerts">
            <app-icon name="bell" [size]="16" />
          </a>
          <div class="user-menu">
            <button type="button" class="user-chip" (click)="toggleMenu($event)">
              <span class="user-avatar">{{ initials() }}</span>
              <app-icon name="arrow-down" [size]="13" />
            </button>
            @if (menuOpen()) {
              <div class="user-dropdown">
                <div class="head">{{ auth.currentUser()?.email }}</div>
                <hr class="sep" />
                <a class="row" routerLink="/profile" (click)="closeMenu()">
                  <app-icon name="user" [size]="14" /> Account
                </a>
                <a class="row" routerLink="/watchlist" (click)="closeMenu()">
                  <app-icon name="heart" [size]="14" /> My watchlist
                </a>
                <a class="row" routerLink="/alerts" (click)="closeMenu()">
                  <app-icon name="bell" [size]="14" /> Price drops
                </a>
                <hr class="sep" />
                <button type="button" class="row" (click)="logout()">
                  <app-icon name="logout" [size]="14" /> Sign out
                </button>
              </div>
            }
          </div>
        } @else {
          <a class="btn ghost" routerLink="/login">Sign in</a>
          <a class="btn primary" routerLink="/register">Get started</a>
        }
      </div>
    </header>
  `,
})
export class NavbarComponent {
  protected readonly auth = inject(AuthService);
  protected readonly theme = inject(ThemeService);
  private readonly liveFeed = inject(LiveFeedService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  protected readonly menuOpen = signal(false);
  protected readonly searchTerm = signal('');

  /** Live-feed status dot: green = connected, amber = reconnecting, red = down. */
  protected readonly wsDotColor = computed(() => {
    switch (this.liveFeed.status()) {
      case 'open':
        return 'var(--success)';
      case 'connecting':
      case 'error':
        return '#f5a623';
      default:
        return 'var(--danger)';
    }
  });

  protected readonly wsDotTitle = computed(() => {
    switch (this.liveFeed.status()) {
      case 'open':
        return 'Live price feed connected';
      case 'connecting':
      case 'error':
        return 'Live price feed reconnecting…';
      default:
        return 'Live price feed offline';
    }
  });

  protected submitSearch(event: Event): void {
    event.preventDefault();
    const q = this.searchTerm().trim();
    if (!q) return;
    this.router.navigate(['/products'], { queryParams: { q } });
  }

  protected initials(): string {
    const user = this.auth.currentUser();
    const source = user?.full_name?.trim() || user?.email || '?';
    return source.slice(0, 2).toUpperCase();
  }

  protected toggleMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.update((v) => !v);
  }

  protected closeMenu(): void {
    this.menuOpen.set(false);
  }

  protected logout(): void {
    this.closeMenu();
    this.auth.logout().subscribe(() => {
      this.toast.info('Signed out.');
      this.router.navigate(['/']);
    });
  }

  /** Close the dropdown on any outside click. */
  @HostListener('document:click', ['$event'])
  protected onDocumentClick(event: MouseEvent): void {
    if (this.menuOpen() && !this.host.nativeElement.contains(event.target as Node)) {
      this.menuOpen.set(false);
    }
  }
}
