import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ThemeService } from './core/services/theme.service';
import { FooterComponent } from './shared/components/footer/footer';
import { NavbarComponent } from './shared/components/navbar/navbar';
import { ToastComponent } from './shared/components/toast/toast';

/**
 * App shell — persistent navbar + footer + toast layer around the routed
 * page outlet. Applies the saved theme on start; the auth session is
 * restored by an app initializer (see app.config.ts) before routing.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, NavbarComponent, FooterComponent, ToastComponent],
  templateUrl: './app.html',
})
export class App {
  private readonly theme = inject(ThemeService);

  constructor() {
    this.theme.init();
  }
}
