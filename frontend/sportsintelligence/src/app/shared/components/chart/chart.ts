/**
 * ChartComponent — a thin, SSR-safe wrapper around Chart.js.
 *
 * Chart.js touches `<canvas>`/`window`, which don't exist during Angular SSR.
 * So the chart is only ever created inside `afterNextRender` (browser-only);
 * on the server this renders an empty canvas and hydrates later. An `effect`
 * keeps the chart in sync when the `config` input changes after creation.
 */
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  afterNextRender,
  effect,
  input,
  viewChild,
} from '@angular/core';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

let chartJsRegistered = false;

@Component({
  selector: 'app-chart',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="chart-box"><canvas #canvas></canvas></div>`,
  styles: [
    `
      .chart-box {
        position: relative;
        width: 100%;
        height: 100%;
        min-height: 260px;
      }
    `,
  ],
})
export class ChartComponent implements OnDestroy {
  readonly config = input.required<ChartConfiguration>();

  private readonly canvasRef =
    viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart?: Chart;

  constructor() {
    afterNextRender(() => {
      if (!chartJsRegistered) {
        Chart.register(...registerables);
        chartJsRegistered = true;
      }
      this.chart = new Chart(this.canvasRef().nativeElement, this.config());
    });

    // Live-update an already-created chart when the config signal changes.
    // No-op on the server (chart is undefined until afterNextRender).
    effect(() => {
      const cfg = this.config();
      if (!this.chart) return;
      this.chart.data = cfg.data;
      this.chart.options = cfg.options ?? {};
      this.chart.update();
    });
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }
}
