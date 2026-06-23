<script lang="ts">
  import type { ViewportState } from "../viewportStore.svelte";
  import { GRID_SIZE } from "../geometry-helpers";

  let { viewport, width, height }: { viewport: ViewportState; width: number; height: number } =
    $props();

  const verticalLines = $derived.by(() => {
    const worldLeft = -viewport.panX / viewport.zoom;
    const worldRight = (width - viewport.panX) / viewport.zoom;
    const startX = Math.floor(worldLeft / GRID_SIZE) * GRID_SIZE;
    const endX = Math.ceil(worldRight / GRID_SIZE) * GRID_SIZE;
    const lines: number[] = [];
    for (let x = startX; x <= endX; x += GRID_SIZE) {
      lines.push(x * viewport.zoom + viewport.panX);
    }
    return lines;
  });

  const horizontalLines = $derived.by(() => {
    const worldTop = -viewport.panY / viewport.zoom;
    const worldBottom = (height - viewport.panY) / viewport.zoom;
    const startY = Math.floor(worldTop / GRID_SIZE) * GRID_SIZE;
    const endY = Math.ceil(worldBottom / GRID_SIZE) * GRID_SIZE;
    const lines: number[] = [];
    for (let y = startY; y <= endY; y += GRID_SIZE) {
      lines.push(y * viewport.zoom + viewport.panY);
    }
    return lines;
  });
</script>

<g class="grid">
  {#each verticalLines as x}
    <line class="grid-line" x1={x} y1={0} x2={x} y2={height} />
  {/each}
  {#each horizontalLines as y}
    <line class="grid-line" x1={0} y1={y} x2={width} y2={y} />
  {/each}
</g>

<style>
  .grid-line {
    stroke: var(--canvas-grid);
    stroke-width: 1;
  }
</style>
