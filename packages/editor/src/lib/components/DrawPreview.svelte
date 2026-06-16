<script lang="ts">
  import type { Point } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import { distance } from "../geometry-helpers";

  let {
    chainPoints,
    snapPoint,
    showSnapRing,
    viewport,
  }: {
    chainPoints: Point[];
    snapPoint: Point | null;
    showSnapRing: boolean;
    viewport: ViewportState;
  } = $props();

  function toScreen(p: Point): Point {
    return worldToScreen(p, viewport);
  }

  const startScreen = $derived(chainPoints.length > 0 ? toScreen(chainPoints[0]) : null);

  const rubberBand = $derived.by(() => {
    if (chainPoints.length === 0 || !snapPoint) return null;
    const from = chainPoints[chainPoints.length - 1];
    const to = snapPoint;
    return {
      from: toScreen(from),
      to: toScreen(to),
      length: distance(from, to),
      mid: toScreen({ x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 }),
    };
  });

  const snapRingScreen = $derived(showSnapRing && snapPoint ? toScreen(snapPoint) : null);
</script>

<g class="draw-preview">
  {#if rubberBand}
    <line
      class="rubber-band"
      x1={rubberBand.from.x}
      y1={rubberBand.from.y}
      x2={rubberBand.to.x}
      y2={rubberBand.to.y}
    />
    <text class="length-label" x={rubberBand.mid.x} y={rubberBand.mid.y - 6} text-anchor="middle">
      {rubberBand.length.toFixed(2)} m
    </text>
  {/if}
  {#if startScreen}
    <circle class="chain-start" cx={startScreen.x} cy={startScreen.y} r="4" />
  {/if}
  {#if snapRingScreen}
    <circle class="snap-ring" cx={snapRingScreen.x} cy={snapRingScreen.y} r="7" />
  {/if}
</g>

<style>
  .rubber-band {
    stroke: #ffb84d;
    stroke-width: 2;
    stroke-dasharray: 6 4;
  }
  .length-label {
    fill: #aaa;
    font-size: 11px;
  }
  .chain-start {
    fill: #ffb84d;
  }
  .snap-ring {
    fill: none;
    stroke: #5af;
    stroke-width: 2;
  }
</style>
