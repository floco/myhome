<script lang="ts">
  import type { DonutSegment } from "./DonutChart.svelte";

  interface Props {
    segments: DonutSegment[];
  }
  let { segments }: Props = $props();

  const maxPct = $derived(Math.max(...segments.map((s) => s.pct), 0.0001));

  function barWidth(seg: DonutSegment): number {
    return Math.round((seg.pct / maxPct) * 100);
  }
</script>

<div class="hbar-chart">
  {#each segments as seg (seg.id)}
    <div class="hbar-row" title="{seg.label}: {seg.valueLabel} ({seg.pct.toFixed(0)}%)">
      <div class="hbar-label">{seg.emoji} {seg.label}</div>
      <div class="hbar-track">
        <div class="hbar-fill" style="width:{barWidth(seg)}%; background:{seg.color}"></div>
      </div>
      <div class="hbar-value">{seg.valueLabel}</div>
    </div>
  {/each}
</div>

<style>
  .hbar-chart { display: flex; flex-direction: column; gap: 2px; width: 100%; }
  .hbar-row { display: flex; align-items: center; gap: 8px; min-height: 22px; }
  .hbar-label {
    flex: 0 0 110px; font-size: 11px; color: var(--text); white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }
  .hbar-track {
    flex: 1; height: 14px; background: var(--surface-alt); border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .hbar-fill { height: 100%; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; min-width: 3px; transition: width .2s; }
  .hbar-value { flex: 0 0 auto; font-size: 11px; color: var(--text-muted); font-weight: 600; min-width: 28px; text-align: right; }
</style>
