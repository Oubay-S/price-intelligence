/**
 * AuthAsideComponent — the showcase panel beside the auth forms.
 *
 * Ports the reference design's `AuthShowcase`: a mock product card whose
 * price ticks down on a timer to dramatise the "alert when it drops"
 * value prop. The timer runs in the browser only (SSR-safe).
 */
import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  PLATFORM_ID,
  inject,
  signal,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

import { IconComponent } from '../../../shared/components/icon/icon';

@Component({
  selector: 'app-auth-aside',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  template: `
    <div style="width:100%;max-width:440px">
      <div class="card" style="padding:20px;border-radius:16px">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
          <div style="width:48px;height:48px;border-radius:10px;background:var(--bg-2);
            display:grid;place-items:center;color:var(--accent)">
            <app-icon name="zap" [size]="20" />
          </div>
          <div>
            <div class="mono" style="font-size:11px;color:var(--text-faint);
              letter-spacing:.1em;text-transform:uppercase">Pacer</div>
            <div style="font-size:14px;font-weight:500">Carbon Plate Racer · US 10</div>
          </div>
        </div>

        <div style="display:flex;align-items:baseline;gap:10px">
          <span class="serif" style="font-size:54px;letter-spacing:-.02em;line-height:1">
            \${{ price().toFixed(2) }}
          </span>
          <span class="pill success mono">
            <app-icon name="arrow-down" [size]="10" /> −27%
          </span>
        </div>
        <div style="margin-top:10px;font-size:12px;color:var(--text-dim)">
          at PeakMart — lowest in 90 days
        </div>

        <hr class="sep" style="margin:16px 0" />

        <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-dim)">
          <span>Target price</span>
          <span class="mono" style="color:var(--accent)">$45.00</span>
        </div>
        <div class="thr-bar" style="margin:10px 0 4px">
          <div class="cur" style="left:72%"></div>
          <div class="tgt" style="left:58%"></div>
        </div>
        <div class="mono" style="display:flex;justify-content:space-between;font-size:11px;
          color:var(--text-faint)">
          <span>$30</span><span>$70</span>
        </div>
      </div>

      <div style="margin-top:18px;display:flex;align-items:center;gap:10px;
        color:var(--text-dim);font-size:13px">
        <app-icon name="bell" [size]="14" />
        Alert triggered when any store drops below target
      </div>
    </div>
  `,
})
export class AuthAsideComponent implements OnDestroy {
  protected readonly price = signal(58.99);
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    if (isPlatformBrowser(inject(PLATFORM_ID))) {
      this.timer = setInterval(() => {
        this.price.update((p) => Math.max(42.8, +(p - 0.3 - Math.random() * 0.4).toFixed(2)));
      }, 900);
    }
  }

  ngOnDestroy(): void {
    if (this.timer) clearInterval(this.timer);
  }
}
