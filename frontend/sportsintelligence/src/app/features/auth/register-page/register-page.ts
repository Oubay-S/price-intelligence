/**
 * RegisterPageComponent — account creation.
 *
 * On success the backend sends a verification email; we route the user to
 * /login with a notice. OAuth buttons are decorative/disabled.
 */
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../../../shared/components/icon/icon';
import { AuthAsideComponent } from '../auth-aside/auth-aside';

/** Group validator — flags `passwordMismatch` when the two fields differ. */
function passwordMatch(group: AbstractControl): ValidationErrors | null {
  const password = group.get('password')?.value;
  const confirm = group.get('confirm_password')?.value;
  return password === confirm ? null : { passwordMismatch: true };
}

@Component({
  selector: 'app-register-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, IconComponent, AuthAsideComponent],
  template: `
    <div class="page fade-up">
      <div class="auth-wrap">
        <div class="auth-left">
          <form class="auth-form" [formGroup]="form" (ngSubmit)="submit()">
            <h2>Create your account.</h2>
            <p class="sub">Free forever. No store logins needed.</p>

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
              <label for="name">Full name</label>
              <input id="name" class="input" type="text" formControlName="full_name"
                placeholder="Alex Morgan" autocomplete="name" />
            </div>

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
                placeholder="At least 8 characters" autocomplete="new-password" />
              @if (showError('password')) {
                <div class="field-error">Password must be at least 8 characters.</div>
              }
            </div>

            <div class="field">
              <label for="confirm_password">Confirm password</label>
              <input id="confirm_password" class="input" type="password"
                formControlName="confirm_password" placeholder="Re-enter your password"
                autocomplete="new-password" />
              @if (showError('confirm_password')) {
                <div class="field-error">Please confirm your password.</div>
              } @else if (form.hasError('passwordMismatch') && form.get('confirm_password')?.touched) {
                <div class="field-error">Passwords do not match.</div>
              }
            </div>

            <button class="btn primary lg" type="submit" style="width:100%;justify-content:center"
              [disabled]="submitting()">
              {{ submitting() ? 'Creating account…' : 'Create account' }}
              <app-icon name="arrow-r" [size]="16" />
            </button>

            <p style="margin-top:18px;color:var(--text-dim);font-size:13px;text-align:center">
              Already have an account?
              <a routerLink="/login" style="color:var(--accent)">Sign in</a>
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
export class RegisterPageComponent {
  protected readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  protected readonly submitting = signal(false);

  protected readonly form = this.fb.nonNullable.group(
    {
      full_name: [''],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirm_password: ['', [Validators.required]],
    },
    { validators: passwordMatch },
  );

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
    const { full_name, email, password } = this.form.getRawValue();
    // confirm_password is client-side only — never sent to the backend.
    this.auth
      .register({ email, password, full_name: full_name || null })
      .subscribe({
        next: () => {
          this.submitting.set(false);
          this.toast.success('Account created — check your inbox to verify your email.');
          this.router.navigate(['/login']);
        },
        error: () => this.submitting.set(false),
      });
  }
}
