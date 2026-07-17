<script lang="ts">
  import type { DonutSegment } from "./DonutChart.svelte";
  import { computeTreemap, cellContentTier } from "../treemapLayout";
  import { textColorForFill } from "../colorContrast";

  interface Props {
    segments: DonutSegment[];
    onsliceclick?: (id: string) => void;
  }
  let { segments, onsliceclick }: Props = $props();

  const WIDTH = 300;
  const HEIGHT = 200;

  interface Cell {
    seg: DonutSegment;
    x: number;
    y: number;
    w: number;
    h: number;
    textColor: string;
    tier: "label" | "icon" | "none";
  }

  const cells = $derived((() => {
    const sorted = [...segments].filter((s) => s.pct > 0).sort((a, b) => b.pct - a.pct);
    const rects = computeTreemap(sorted.map((s) => s.pct), WIDTH, HEIGHT);
    return sorted.map((seg, i): Cell => {
      const r = rects[i];
      return {
        seg,
        x: r.x,
        y: r.y,
        w: r.w,
        h: r.h,
        textColor: textColorForFill(seg.color),
        tier: cellContentTier(r.w, r.h),
      };
    });
  })());
</script>

<svg viewBox="0 0 {WIDTH} {HEIGHT}" width={WIDTH} height={HEIGHT}>
  {#each cells as cell (cell.seg.id)}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <g style="cursor:{onsliceclick ? 'pointer' : 'default'}" onclick={() => onsliceclick?.(cell.seg.id)}>
      <title>{cell.seg.label}: {cell.seg.valueLabel} ({cell.seg.pct.toFixed(0)}%)</title>
      <rect
        x={cell.x + 1}
        y={cell.y + 1}
        width={Math.max(cell.w - 2, 0)}
        height={Math.max(cell.h - 2, 0)}
        fill={cell.seg.color}
        rx="3"
      />
      {#if cell.tier === "label"}
        <text x={cell.x + 6} y={cell.y + 15} fill={cell.textColor} font-size="10" font-family="sans-serif" font-weight="600">{cell.seg.emoji} {cell.seg.label}</text>
        <text x={cell.x + 6} y={cell.y + 28} fill={cell.textColor} font-size="9" font-family="sans-serif" opacity="0.85">{cell.seg.valueLabel} · {cell.seg.pct.toFixed(0)}%</text>
      {:else if cell.tier === "icon"}
        <text x={cell.x + cell.w / 2} y={cell.y + cell.h / 2 + 4} text-anchor="middle" fill={cell.textColor} font-size="13">{cell.seg.emoji}</text>
      {/if}
    </g>
  {/each}
</svg>

<style>
  svg { overflow: visible; }
</style>
