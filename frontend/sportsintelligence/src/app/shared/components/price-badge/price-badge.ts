/**
 * PriceBadgeComponent — compact price-trend indicator.
 *
 * Shows a direction arrow + optional percentage, colour-coded by trend
 * (falling = green/good, rising = red, stable = neutral).
 *
 *   <app-price-badge [trend]="product.pricing.trend" [pct]="product.pricing.discount_pct" />
 */
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { PriceTrend } from '../../../core/models';
import { IconComponent } from '../icon/icon';

@Component({
  selector: 'app-price-badge',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  template: `
    <span class="price-badge" [class]="trend()">
      <app-icon [name]="iconName()" [size]="11" />
      @if (pct() != null) {
        <span>{{ sign() }}{{ absPct() }}%</span>
      } @else {
        <span>{{ label() }}</span>
      }
    </span>
  `,
})
export class PriceBadgeComponent {
  readonly trend = input<PriceTrend>('stable');
  /** Optional magnitude — e.g. discount % or period change %. */
  readonly pct = input<number | null | undefined>(null);

  protected readonly iconName = computed(() => {
    switch (this.trend()) {
      case 'falling': return 'arrow-down' as const;
      case 'rising': return 'arrow-up' as const;
      default: return 'minus' as const;
    }
  });

  protected readonly label = computed(() => {
    switch (this.trend()) {
      case 'falling': return 'Falling';
      case 'rising': return 'Rising';
      default: return 'Stable';
    }
  });

  protected readonly absPct = computed(() => Math.abs(this.pct() ?? 0).toFixed(1));
  protected readonly sign = computed(() => (this.trend() === 'rising' ? '+' : '−'));
}
