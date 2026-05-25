/**
 * LoginPageComponent — email/password sign-in.
 *
 * OAuth (Google/GitHub) buttons are rendered for design fidelity but
 * disabled — the backend exposes no OAuth endpoints.
 */
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../../../shared/components/icon/icon';
import { AuthAsideComponent } from '../auth-aside/auth-aside';

@Component({
  selector: 'app-login-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, IconComponent, AuthAsideComponent],
  template: `
    <div class="page fade-up">
      <div class="auth-wrap">
        <div class="auth-left">
          <form class="auth-form" [formGroup]="form" (ngSubmit)="submit()">
            <h2>Welcome back.</h2>
            <p class="sub">Sign in to pick up where you left off.</p>

            @if (auth.authError(); as err) {
              <div class="auth-banner error">{{ err }}</div>
            }

            <div class="oauth-row">
              <button type="button" class="btn ghost" disabled title="OAuth not available yet"
                style="justify-content:center">
                <app-icon name="globe" [size]="16" /> Google
              </button>
              <button type="button" class="btn ghost" disabled title="OAuth not available yet"
                style="justify-content:center">
                <app-icon name="globe" [size]="16" /> GitHub
              </button>
            </div>
            <div class="divider">or continue with email</div>

            <div class="field">
              <label for="email">Email</label>
              <input id="email" class="input" type="email" formControlName="email"
                placeholder="you@sports.com" autocomplete="email" />
              @if (showError('email')) {
                <div class="field-error">Enter a valid email address.</div>
              }
            </div>

            <div class="field">
              <label for="password">Password</label>
              <input id="password" class="input" type="password" formControlName="password"
                placeholder="••••••••" autocomplete="current-password" />
              @if (showError('password')) {
                <div class="field-error">Password is required.</div>
              }
            </div>

            <button class="btn primary lg" type="submit" style="width:100%;justify-content:center"
              [disabled]="submitting()">
              {{ submitting() ? 'Signing in…' : 'Sign in' }}
              <app-icon name="arrow-r" [size]="16" />
            </button>

            <p style="margin-top:18px;color:var(--text-dim);font-size:13px;text-align:center">
              Don't have an account?
              <a routerLink="/register" style="color:var(--accent)">Create one</a>
            </p>
          </form>
        </div>
        <div class="auth-right">
          <div class="auth-right-inner"><app-auth-aside /></div>
        </div>
      </div>
    </div>
  `,
})
export class LoginPageComponent {
  protected readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly submitting = signal(false);

  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  protected showError(control: string): boolean {
    const c = this.form.get(control);
    return !!c && c.invalid && (c.dirty || c.touched);
  }

  protected submit(): void {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.auth.login(this.form.getRawValue()).subscribe({
      next: (user) => {
        this.submitting.set(false);
        this.toast.success(`Signed in as ${user.email}`);
        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl') ?? '/products';
        this.router.navigateByUrl(returnUrl);
      },
      error: () => this.submitting.set(false),
    });
  }
}
