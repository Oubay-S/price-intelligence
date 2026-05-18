/**
 * PriceChartComponent — Chart.js line chart for price time-series.
 *
 * Thin wrapper around chart.js v4. The dashboard / detail pages feed it
 * `labels` + `values`; it draws a gradient-filled line styled with the
 * design-system accent colour.
 *
 * SSR-safe: Chart.js touches the canvas + window, so the chart is only
 * created in the browser (`afterNextRender`). An `effect` rebuilds it
 * whenever the inputs change.
 */
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  PLATFORM_ID,
  afterNextRender,
  effect,
  inject,
  input,
  viewChild,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import {
  CategoryScale,
  Chart,
  Filler,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js';

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
);

@Component({
  selector: 'app-price-chart',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="chart-host" [style.height]="height()">
      <canvas #canvas></canvas>
    </div>
  `,
})
export class PriceChartComponent {
  /** X-axis labels (dates). */
  readonly labels = input<string[]>([]);
  /** Y-axis values (MAD prices) — same length as labels. */
  readonly values = input<number[]>([]);
  readonly height = input('320px');
  /** Series label shown in the tooltip. */
  readonly seriesLabel = input('Price (MAD)');

  private readonly canvasRef = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  private chart: Chart | null = null;
  private ready = false;

  constructor() {
    afterNextRender(() => {
      this.ready = true;
      this.render();
    });

    // Rebuild when inputs change (after the canvas exists).
    effect(() => {
      this.labels();
      this.values();
      this.seriesLabel();
      if (this.ready) this.render();
    });
  }

  private render(): void {
    if (!this.isBrowser) return;
    const canvas = this.canvasRef().nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const accent = this.cssVar('--accent', '#c8ff2c');
    const line = this.cssVar('--line', '#23272f');
    const textDim = this.cssVar('--text-dim', '#9aa3ae');

    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, this.hexAlpha(accent, 0.35));
    gradient.addColorStop(1, this.hexAlpha(accent, 0));

    if (this.chart) {
      this.chart.data.labels = this.labels();
      this.chart.data.datasets[0].data = this.values();
      this.chart.data.datasets[0].label = this.seriesLabel();
      this.chart.update();
      return;
    }

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: this.labels(),
        datasets: [
          {
            label: this.seriesLabel(),
            data: this.values(),
            borderColor: accent,
            backgroundColor: gradient,
            borderWidth: 1.8,
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: accent,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          tooltip: {
            displayColors: false,
            callbacks: {
              label: (item) => `$${Number(item.parsed.y).toFixed(2)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: line },
            ticks: { color: textDim, maxTicksLimit: 7, font: { size: 10 } },
          },
          y: {
            grid: { color: line },
            ticks: {
              color: textDim,
              font: { size: 10 },
              callback: (v) => `$${v}`,
            },
          },
        },
      },
    });
  }

  /** Read a CSS custom property off <html>, with a fallback. */
  private cssVar(name: string, fallback: string): string {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  /** Apply an alpha to a hex colour (#rrggbb) → rgba(). */
  private hexAlpha(hex: string, alpha: number): string {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!m) return hex;
    const [r, g, b] = [m[1], m[2], m[3]].map((h) => parseInt(h, 16));
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
}
