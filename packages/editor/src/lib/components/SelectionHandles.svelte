<script lang="ts">
  import type { Point, Wall } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import { distance } from "../geometry-helpers";

  let {
    wall,
    viewport,
    draggingPoint,
    ondragstart,
  }: {
    wall: Wall;
    viewport: ViewportState;
    draggingPoint: Point | null;
    ondragstart: (point: Point, event: PointerEvent) => void;
  } = $props();

  function toScreen(p: Point): Point {
    return worldToScreen(p, viewport);
  }

  const startScreen = $derived(toScreen(wall.start));
  const endScreen = $derived(toScreen(wall.end));
  const midScreen = $derived(toScreen({ x: (wall.start.x + wall.end.x) / 2, y: (wall.start.y + wall.end.y) / 2 }));
  const length = $derived(distance(wall.start, wall.end));
</script>

<g class="selection-handles">
  <circle
    class="handle"
    cx={startScreen.x}
    cy={startScreen.y}
    r="5"
    onpointerdown={(e) => ondragstart(wall.start, e)}
  />
  <circle
    class="handle"
    cx={endScreen.x}
    cy={endScreen.y}
    r="5"
    onpointerdown={(e) => ondragstart(wall.end, e)}
  />
  {#if draggingPoint}
    <text class="length-label" x={midScreen.x} y={midScreen.y - 6} text-anchor="middle">
      {length.toFixed(2)} m
    </text>
  {/if}
</g>

<style>
  .handle {
    fill: var(--canvas-wall-selected);
    stroke: var(--text);
    stroke-width: 1;
    cursor: grab;
  }
  .length-label {
    fill: var(--canvas-label);
    font-size: 11px;
  }
</style>
