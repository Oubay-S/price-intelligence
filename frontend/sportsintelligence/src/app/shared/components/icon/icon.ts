/**
 * IconComponent — inline stroke-icon set.
 *
 * Ported from the reference design's `icons.jsx`. Renders a single SVG by
 * name; `currentColor` makes it inherit text colour. Usage:
 *   <app-icon name="bell" [size]="16" />
 */
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export type IconName =
  | 'search' | 'bell' | 'user' | 'heart' | 'heart-f' | 'chart' | 'compare'
  | 'grid' | 'arrow-r' | 'arrow-down' | 'arrow-up' | 'check' | 'x'
  | 'filter' | 'sort' | 'settings' | 'tag' | 'zap' | 'globe' | 'shield'
  | 'plus' | 'minus' | 'logout' | 'sun' | 'moon';

@Component({
  selector: 'app-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      [attr.width]="size()"
      [attr.height]="size()"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      [attr.stroke-width]="stroke()"
      stroke-linecap="round"
      stroke-linejoin="round"
      [attr.aria-hidden]="true"
    >
      @switch (name()) {
        @case ('search') { <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /> }
        @case ('bell') { <path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9" /><path d="M10 21a2 2 0 0 0 4 0" /> }
        @case ('user') { <circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-7 8-7s8 3 8 7" /> }
        @case ('heart') { <path d="M12 20s-7-4.5-9.5-9.5C.5 5.5 5 2.5 8 4.5 10 5.8 12 8 12 8s2-2.2 4-3.5c3-2 7.5 1 5.5 6-2.5 5-9.5 9.5-9.5 9.5Z" /> }
        @case ('heart-f') { <path fill="currentColor" d="M12 20s-7-4.5-9.5-9.5C.5 5.5 5 2.5 8 4.5 10 5.8 12 8 12 8s2-2.2 4-3.5c3-2 7.5 1 5.5 6-2.5 5-9.5 9.5-9.5 9.5Z" /> }
        @case ('chart') { <path d="M3 3v18h18" /><path d="M7 15l4-5 3 3 6-8" /> }
        @case ('compare') { <path d="M4 6h16M4 6l3-3M4 6l3 3" /><path d="M20 18H4m16 0-3-3m3 3-3 3" /> }
        @case ('grid') { <rect x="3" y="3" width="8" height="8" rx="1.5" /><rect x="13" y="3" width="8" height="8" rx="1.5" /><rect x="3" y="13" width="8" height="8" rx="1.5" /><rect x="13" y="13" width="8" height="8" rx="1.5" /> }
        @case ('arrow-r') { <path d="M5 12h14m0 0-5-5m5 5-5 5" /> }
        @case ('arrow-down') { <path d="M12 5v14m0 0-5-5m5 5 5-5" /> }
        @case ('arrow-up') { <path d="M12 19V5m0 0-5 5m5-5 5 5" /> }
        @case ('check') { <path d="m5 12 5 5 9-10" /> }
        @case ('x') { <path d="M6 6l12 12M18 6 6 18" /> }
        @case ('filter') { <path d="M4 5h16M7 12h10M10 19h4" /> }
        @case ('sort') { <path d="M8 4v16m0 0-3-3m3 3 3-3M16 20V4m0 0-3 3m3-3 3 3" /> }
        @case ('settings') { <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" /> }
        @case ('tag') { <path d="M3 12V3h9l9 9-9 9-9-9Z" /><circle cx="7.5" cy="7.5" r="1.2" fill="currentColor" /> }
        @case ('zap') { <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" /> }
        @case ('globe') { <circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a13 13 0 0 1 0 18M12 3a13 13 0 0 0 0 18" /> }
        @case ('shield') { <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z" /> }
        @case ('plus') { <path d="M12 5v14M5 12h14" /> }
        @case ('minus') { <path d="M5 12h14" /> }
        @case ('logout') { <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /> }
        @case ('sun') { <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5" /> }
        @case ('moon') { <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" /> }
      }
    </svg>
  `,
})
export class IconComponent {
  readonly name = input.required<IconName>();
  readonly size = input(16);
  readonly stroke = input(1.5);
}
