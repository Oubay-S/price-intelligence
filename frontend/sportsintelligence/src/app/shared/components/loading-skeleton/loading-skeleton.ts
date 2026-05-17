/**
 * LoadingSkeletonComponent — shimmer placeholders for loading states.
 *
 *   <app-loading-skeleton variant="card-grid" [count]="6" />
 *   <app-loading-skeleton variant="line" [count]="3" />
 *   <app-loading-skeleton variant="block" height="360px" />
 */
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type SkeletonVariant = 'line' | 'block' | 'card-grid' | 'rows';

@Component({
  selector: 'app-loading-skeleton',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @switch (variant()) {
      @case ('card-grid') {
        <div class="cat-grid">
          @for (i of items(); track i) {
            <div class="card" style="overflow:hidden">
              <div class="shimmer" style="aspect-ratio:1.2/1;border-radius:0"></div>
              <div style="padding:14px;display:flex;flex-direction:column;gap:8px">
                <div class="shimmer" style="height:10px;width:40%"></div>
                <div class="shimmer" style="height:14px;width:80%"></div>
                <div class="shimmer" style="height:24px;width:50%;margin-top:6px"></div>
              </div>
            </div>
          }
        </div>
      }
      @case ('rows') {
        <div style="display:flex;flex-direction:column;gap:10px">
          @for (i of items(); track i) {
            <div class="shimmer" style="height:72px"></div>
          }
        </div>
      }
      @case ('block') {
        <div class="shimmer" [style.height]="height()" style="width:100%"></div>
      }
      @default {
        <div style="display:flex;flex-direction:column;gap:8px">
          @for (i of items(); track i) {
            <div class="shimmer" [style.height]="height()" style="width:100%"></div>
          }
        </div>
      }
    }
  `,
})
export class LoadingSkeletonComponent {
  readonly variant = input<SkeletonVariant>('line');
  readonly count = input(3);
  readonly height = input('14px');

  protected readonly items = computed(() => Array.from({ length: this.count() }, (_, i) => i));
}
