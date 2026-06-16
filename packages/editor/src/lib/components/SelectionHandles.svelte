<script lang="ts">
  import type { Point, Wall } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";

  let {
    wall,
    viewport,
    ondragstart,
  }: {
    wall: Wall;
    viewport: ViewportState;
    ondragstart: (point: Point, event: MouseEvent) => void;
  } = $props();

  function toScreen(p: Point): Point {
    return worldToScreen(p, viewport);
  }

  const startScreen = $derived(toScreen(wall.start));
  const endScreen = $derived(toScreen(wall.end));
</script>

<g class="selection-handles">
  <circle
    class="handle"
    cx={startScreen.x}
    cy={startScreen.y}
    r="5"
    onmousedown={(e) => ondragstart(wall.start, e)}
  />
  <circle
    class="handle"
    cx={endScreen.x}
    cy={endScreen.y}
    r="5"
    onmousedown={(e) => ondragstart(wall.end, e)}
  />
</g>

<style>
  .handle {
    fill: #5af;
    stroke: #fff;
    stroke-width: 1;
    cursor: grab;
  }
</style>
