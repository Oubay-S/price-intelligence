/**
 * ProductCardComponent — catalogue grid tile.
 *
 * Pure presentational: takes a ProductResponse, links to the detail page,
 * and emits `watchlistToggle` (heart) / `compareSelect` (compare) when the
 * action buttons are clicked. The parent owns the actual add/remove call
 * and the `inWatchlist` state.
 */
import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';

import { CATEGORY_LABELS, ProductResponse } from '../../../core/models';
import { IconComponent } from '../icon/icon';
import { PriceBadgeComponent } from '../price-badge/price-badge';

@Component({
  selector: 'app-product-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, CurrencyPipe, DecimalPipe, IconComponent, PriceBadgeComponent],
  template: `
    <article class="prod">
      <a class="prod-img" [routerLink]="['/products', product().canonical_product_id]">
        @if (product().image_url) {
          <img [src]="product().image_url" [alt]="product().name" loading="lazy" />
        } @else {
          <span class="ph-glyph"><app-icon name="grid" [size]="32" /></span>
        }
        <div class="lbl">
          <span>{{ product().flavour || product().site }}</span>
          <span>{{ categoryLabel() }}</span>
        </div>
        @if (discountPct() >= 15) {
          <span
            class="pill accent"
            style="position:absolute;top:10px;left:10px;font-size:10px;padding:2px 8px"
          >−{{ discountPct() | number: '1.0-0' }}% off</span>
        }
      </a>

      <a class="prod-body" [routerLink]="['/products', product().canonical_product_id]">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
          <span class="prod-brand">{{ product().brand_raw }}</span>
          <span
            class="pill"
            style="font-size:9px;padding:1px 7px;letter-spacing:.04em;text-transform:none"
            >{{ product().site }}</span
          >
        </div>
        <span class="prod-name">{{ product().name }}</span>
        <div class="prod-meta">
          @if (product().ratings) {
            <span>★ {{ product().ratings!.score | number: '1.1-1' }}</span>
            <span style="color:var(--text-faint)">·</span>
            <span>{{ product().ratings!.count | number }} reviews</span>
          } @else {
            <span>No ratings yet</span>
          }
        </div>
      </a>

      <div class="prod-foot">
        <div class="prod-price">
          <span class="cur">{{ product().pricing.current | currency: 'MAD' }}</span>
          @if (product().pricing.original) {
            <span class="was">{{ product().pricing.original | currency: 'MAD' }}</span>
          }
        </div>
        <div style="display:flex;align-items:center;gap:6px">
          <app-price-badge [trend]="product().pricing.trend" />
          <button
            type="button"
            class="iconbtn"
            aria-label="Compare across stores"
            (click)="compareSelect.emit(product())"
          >
            <app-icon name="compare" [size]="14" />
          </button>
          <button
            type="button"
            class="iconbtn"
            [class.on]="inWatchlist()"
            [attr.aria-pressed]="inWatchlist()"
            [attr.aria-label]="inWatchlist() ? 'Remove from watchlist' : 'Add to watchlist'"
            (click)="watchlistToggle.emit(product())"
          >
            <app-icon [name]="inWatchlist() ? 'heart-f' : 'heart'" [size]="14" />
          </button>
        </div>
      </div>
    </article>
  `,
})
export class ProductCardComponent {
  readonly product = input.required<ProductResponse>();
  readonly inWatchlist = input(false);

  readonly watchlistToggle = output<ProductResponse>();
  readonly compareSelect = output<ProductResponse>();

  protected readonly categoryLabel = computed(
    () => CATEGORY_LABELS[this.product().category] ?? this.product().category,
  );

  protected readonly discountPct = computed(() => this.product().pricing.discount_pct ?? 0);
}
