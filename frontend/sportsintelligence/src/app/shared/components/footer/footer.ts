/**
 * FooterComponent — static site footer strip.
 */
import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-footer',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <footer class="footer">
      <div>© {{ year }} PriceIntelligent — Sports price intelligence</div>
      <div class="mono">batch + streaming pipeline · refreshed every 15 min</div>
    </footer>
  `,
})
export class FooterComponent {
  protected readonly year = new Date().getFullYear();
}
