<script lang="ts">
  import type { DonutSegment } from "./DonutChart.svelte";
  import { textColorForFill } from "../colorContrast";

  interface Props {
    segments: DonutSegment[];
  }
  let { segments }: Props = $props();

  // A segment narrower than this can't plausibly hold its value text without
  // spilling into its neighbors, so the number is dropped (the legend below
  // always has the exact value regardless).
  const INSIDE_VALUE_MIN_PCT = 8;
</script>

<div class="stacked-bar-chart">
  <div class="stacked-bar">
    {#each segments as seg (seg.id)}
      <div
        class="stacked-segment"
        style="width:{seg.pct}%; background:{seg.color}; color:{textColorForFill(seg.color)}"
        title="{seg.label}: {seg.valueLabel} ({seg.pct.toFixed(0)}%)"
      >{seg.pct >= INSIDE_VALUE_MIN_PCT ? seg.valueLabel : ""}</div>
    {/each}
  </div>
  <div class="stacked-legend">
    {#each segments as seg (seg.id)}
      <div class="legend-item">
        <span class="legend-label">{seg.emoji} {seg.label}</span>
        <span class="legend-value">{seg.valueLabel}</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .stacked-bar-chart { display: flex; flex-direction: column; gap: 10px; width: 100%; }
  .stacked-bar {
    display: flex;
    width: 100%;
    height: 36px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: var(--surface-alt);
  }
  .stacked-segment {
    height: 100%;
    min-width: 3px;
    box-sizing: border-box;
    border-right: 2px solid var(--surface-alt);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    overflow: hidden;
    white-space: nowrap;
    transition: width .2s;
  }
  .stacked-segment:last-child { border-right: none; }
  .stacked-legend { display: flex; flex-flow: row wrap; gap: 6px 16px; }
  .legend-item { display: flex; align-items: center; gap: 4px; font-size: 11px; white-space: nowrap; }
  .legend-label { color: var(--text); }
  .legend-value { color: var(--text-muted); font-weight: 600; }
</style>
