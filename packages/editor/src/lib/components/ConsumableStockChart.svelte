<script lang="ts">
  import { _ } from "svelte-i18n";
  import { formatDate } from "../dateFormat";
  import type { ConsumableTransaction } from "../consumableStore.svelte";

  interface Props {
    transactions: ConsumableTransaction[];
    unit: string;
    minQuantity: number;
  }

  let { transactions, unit, minQuantity }: Props = $props();

  const VIEW_W = 520;
  const VIEW_H = 200;
  const PAD_L = 34;
  const PAD_R = 12;
  const PAD_T = 12;
  const PAD_B = 24;
  const PLOT_W = VIEW_W - PAD_L - PAD_R;
  const PLOT_H = VIEW_H - PAD_T - PAD_B;

  const points = $derived(
    transactions
      .slice()
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .map((tx) => ({ t: new Date(tx.timestamp).getTime(), y: tx.quantityAfter, tx })),
  );

  const hasChart = $derived(points.length >= 2);

  const domain = $derived((() => {
    const ts = points.map((p) => p.t);
    const ys = points.map((p) => p.y);
    const tMin = Math.min(...ts);
    const tMax = Math.max(...ts);
    const rawMax = Math.max(...ys, minQuantity, 1);
    return { tMin: tMin === tMax ? tMin - 1 : tMin, tMax, yMax: rawMax * 1.15 };
  })());

  function scaleX(t: number): number {
    const { tMin, tMax } = domain;
    if (tMax === tMin) return PAD_L + PLOT_W / 2;
    return PAD_L + ((t - tMin) / (tMax - tMin)) * PLOT_W;
  }
  function scaleY(y: number): number {
    return PAD_T + PLOT_H - (y / domain.yMax) * PLOT_H;
  }

  const screenPoints = $derived(points.map((p) => ({ x: scaleX(p.t), y: scaleY(p.y), data: p })));

  const linePath = $derived(
    screenPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" "),
  );
  const areaPath = $derived(
    screenPoints.length > 0
      ? `${linePath} L ${screenPoints[screenPoints.length - 1].x} ${PAD_T + PLOT_H} L ${screenPoints[0].x} ${PAD_T + PLOT_H} Z`
      : "",
  );

  const yTicks = $derived([0, domain.yMax / 2, domain.yMax]);

  const minLineY = $derived(scaleY(minQuantity));
  const showMinLine = $derived(minQuantity > 0 && minQuantity <= domain.yMax);

  let svgEl = $state<SVGSVGElement | undefined>(undefined);
  let hoverIndex = $state<number | null>(null);

  function handlePointerMove(e: PointerEvent): void {
    if (!svgEl || screenPoints.length === 0) return;
    const rect = svgEl.getBoundingClientRect();
    if (rect.width === 0) return;
    const localX = ((e.clientX - rect.left) / rect.width) * VIEW_W;
    let nearest = 0;
    let nearestDist = Infinity;
    screenPoints.forEach((p, i) => {
      const d = Math.abs(p.x - localX);
      if (d < nearestDist) { nearestDist = d; nearest = i; }
    });
    hoverIndex = nearest;
  }
  function handlePointerLeave(): void {
    hoverIndex = null;
  }

  const hovered = $derived(hoverIndex !== null ? screenPoints[hoverIndex] : null);

  function formatQty(n: number): string {
    return n % 1 === 0 ? String(n) : n.toFixed(1);
  }
</script>

{#if !hasChart}
  <div class="chart-empty">{$_('consumables.modal.notEnoughHistory')}</div>
{:else}
  <div class="chart-wrap" style="aspect-ratio: {VIEW_W} / {VIEW_H};">
    <svg
      bind:this={svgEl}
      viewBox="0 0 {VIEW_W} {VIEW_H}"
      class="chart-svg"
      onpointermove={handlePointerMove}
      onpointerleave={handlePointerLeave}
    >
      {#each yTicks as tick}
        <line x1={PAD_L} y1={scaleY(tick)} x2={VIEW_W - PAD_R} y2={scaleY(tick)} stroke="var(--border)" stroke-width="1" />
        <text x={PAD_L - 6} y={scaleY(tick)} text-anchor="end" dominant-baseline="middle" font-size="9" fill="var(--text-faint)" font-family="sans-serif">{formatQty(tick)}</text>
      {/each}

      {#if showMinLine}
        <line x1={PAD_L} y1={minLineY} x2={VIEW_W - PAD_R} y2={minLineY} stroke="var(--warning)" stroke-width="1" stroke-dasharray="3,2" />
      {/if}

      <path d={areaPath} fill="var(--chart-series-1)" opacity="0.1" stroke="none" />
      <path d={linePath} fill="none" stroke="var(--chart-series-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />

      {#each screenPoints as p (p.data.tx.id)}
        <circle cx={p.x} cy={p.y} r="4" fill="var(--chart-series-1)" stroke="var(--surface)" stroke-width="2" />
      {/each}

      <text x={screenPoints[0].x} y={VIEW_H - 6} text-anchor="start" font-size="9" fill="var(--text-faint)" font-family="sans-serif">{formatDate(points[0].tx.timestamp)}</text>
      <text x={screenPoints[screenPoints.length - 1].x} y={VIEW_H - 6} text-anchor="end" font-size="9" fill="var(--text-faint)" font-family="sans-serif">{formatDate(points[points.length - 1].tx.timestamp)}</text>

      {#if hovered}
        <line x1={hovered.x} y1={PAD_T} x2={hovered.x} y2={PAD_T + PLOT_H} stroke="var(--text-faint)" stroke-width="1" />
        <circle cx={hovered.x} cy={hovered.y} r="6" fill="var(--chart-series-1)" stroke="var(--surface)" stroke-width="2" />
      {/if}
    </svg>

    {#if hovered}
      <div
        class="chart-tooltip"
        class:tooltip-right={hovered.x / VIEW_W > 0.6}
        style="left:{(hovered.x / VIEW_W) * 100}%; top:{(hovered.y / VIEW_H) * 100}%"
      >
        <div class="chart-tooltip-value">{formatQty(hovered.data.y)} {unit}</div>
        <div class="chart-tooltip-date">{formatDate(hovered.data.tx.timestamp)}</div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .chart-empty {
    display: flex; align-items: center; justify-content: center;
    min-height: 120px; color: var(--text-faint); font-size: 12px; font-style: italic;
  }
  .chart-wrap { position: relative; width: 100%; }
  .chart-svg { width: 100%; height: 100%; display: block; cursor: crosshair; }
  .chart-tooltip {
    position: absolute; transform: translate(-50%, -100%) translateY(-10px);
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 4px 8px; font-size: 11px; white-space: nowrap; pointer-events: none;
    box-shadow: var(--shadow-sm); z-index: 1;
  }
  .chart-tooltip.tooltip-right { transform: translate(-90%, -100%) translateY(-10px); }
  .chart-tooltip-value { font-weight: 600; color: var(--text); }
  .chart-tooltip-date { color: var(--text-faint); }
</style>
