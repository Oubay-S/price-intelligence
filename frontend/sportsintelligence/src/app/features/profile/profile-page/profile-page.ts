/**
 * ProfilePageComponent — the signed-in user's account page.
 *
 * Auth-gated (authGuard). Shows identity from `AuthService.currentUser()`,
 * email-verification status, member-since date, a watchlist count pulled
 * from `GET /watchlist`, and quick links + sign-out.
 */
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Router, RouterLink } from '@angular/router';

import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../../../shared/components/icon/icon';

@Component({
  selector: 'app-profile-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, IconComponent],
  template: `
    <div class="page fade-up">
      <div class="container narrow" style="padding-top:40px;padding-bottom:80px">
        @if (auth.currentUser(); as u) {
          <div class="wl-head">
            <div>
              <h1 class="serif" style="margin:0;font-size:44px;letter-spacing:-.02em;
                font-weight:400">Account</h1>
              <p style="color:var(--text-dim);margin:8px 0 0">
                Your PriceIntelligent profile and tracking activity.
              </p>
            </div>
            <button class="btn ghost" (click)="logout()">
              <app-icon name="logout" [size]="14" /> Sign out
            </button>
          </div>

          <div class="card elev" style="padding:28px;display:flex;align-items:center;gap:20px">
            <span class="user-avatar" style="width:64px;height:64px;font-size:24px;
              display:grid;place-items:center;border-radius:14px;
              background:var(--accent);color:var(--accent-ink);font-weight:600">
              {{ initials() }}
            </span>
            <div style="flex:1">
              <div style="font-size:20px;font-weight:600">{{ u.full_name || 'No name set' }}</div>
              <div style="color:var(--text-dim);font-size:14px">{{ u.email }}</div>
              <div class="tags" style="margin-top:8px">
                <span class="pill">{{ u.role }}</span>
                <span class="pill" [style.color]="u.email_verified ? 'var(--accent)' : 'var(--text-dim)'">
                  <app-icon name="shield" [size]="10" />
                  {{ u.email_verified ? 'Email verified' : 'Email not verified' }}
                </span>
              </div>
            </div>
          </div>

          <div class="card" style="margin-top:16px">
            <div style="padding:14px 20px;border-bottom:1px solid var(--line);font-weight:500">
              Account details
            </div>
            <div style="padding:6px 20px">
              <div class="detail-row">
                <span>Member since</span>
                <span>{{ u.created_at | date: 'longDate' }}</span>
              </div>
              <div class="detail-row">
                <span>Last sign-in</span>
                <span>{{ u.last_login_at ? (u.last_login_at | date: 'medium') : '—' }}</span>
              </div>
              <div class="detail-row">
                <span>Account status</span>
                <span>{{ u.is_active ? 'Active' : 'Inactive' }}</span>
              </div>
              <div class="detail-row">
                <span>Tracked products</span>
                <span>{{ watchCount() === null ? '…' : watchCount() }}</span>
              </div>
            </div>
          </div>

          <div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap">
            <a class="btn ghost" routerLink="/watchlist">
              <app-icon name="heart" [size]="14" /> My watchlist
            </a>
            <a class="btn ghost" routerLink="/alerts">
              <app-icon name="bell" [size]="14" /> Price drops
            </a>
          </div>
        }
      </div>
    </div>
  `,
  styles: [
    `
      .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        font-size: 14px;
        border-bottom: 1px solid var(--line);
      }
      .detail-row:last-child {
        border-bottom: none;
      }
      .detail-row span:first-child {
        color: var(--text-dim);
      }
    `,
  ],
})
export class ProfilePageComponent {
  protected readonly auth = inject(AuthService);
  private readonly api = inject(ApiService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  protected readonly watchCount = signal<number | null>(null);

  protected readonly initials = computed(() => {
    const user = this.auth.currentUser();
    const source = user?.full_name?.trim() || user?.email || '?';
    return source.slice(0, 2).toUpperCase();
  });

  constructor() {
    this.api.getWatchlist(1, 100).subscribe({
      next: (res) => this.watchCount.set(res.items.length),
      error: () => this.watchCount.set(0),
    });
  }

  protected logout(): void {
    this.auth.logout().subscribe(() => {
      this.toast.info('Signed out.');
      this.router.navigate(['/']);
    });
  }
}
