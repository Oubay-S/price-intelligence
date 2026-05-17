/**
 * ToastComponent — renders the global toast stack.
 *
 * Mounted once in the app shell. Reads ToastService.toasts and lets the
 * user dismiss each toast early.
 */
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { ToastService } from '../../../core/services/toast.service';
import { IconComponent } from '../icon/icon';

@Component({
  selector: 'app-toast',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  template: `
    @if (toast.toasts().length) {
      <div class="toast-stack" role="status" aria-live="polite">
        @for (t of toast.toasts(); track t.id) {
          <div class="toast" [class]="t.kind">
            <span class="bar"></span>
            <span>{{ t.message }}</span>
            <button type="button" (click)="toast.dismiss(t.id)" aria-label="Dismiss">
              <app-icon name="x" [size]="13" />
            </button>
          </div>
        }
      </div>
    }
  `,
})
export class ToastComponent {
  protected readonly toast = inject(ToastService);
}
