<script lang="ts">
  import type { Wall } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte";

  let {
    wall,
    viewport,
    selected = false,
    onselect,
  }: {
    wall: Wall;
    viewport: ViewportState;
    selected?: boolean;
    onselect?: (id: string) => void;
  } = $props();

  const x1 = $derived(wall.start.x * viewport.zoom + viewport.panX);
  const y1 = $derived(wall.start.y * viewport.zoom + viewport.panY);
  const x2 = $derived(wall.end.x * viewport.zoom + viewport.panX);
  const y2 = $derived(wall.end.y * viewport.zoom + viewport.panY);

  function handleClick(event: MouseEvent): void {
    event.stopPropagation();
    onselect?.(wall.id);
  }
</script>

<line
  {x1}
  {y1}
  {x2}
  {y2}
  class="divider"
  class:selected
  onclick={handleClick}
  role="button"
  tabindex="0"
/>

<style>
  .divider {
    stroke: #9ad;
    stroke-width: 2;
    stroke-dasharray: 6 4;
    cursor: pointer;
  }
  .divider.selected {
    stroke: #5af;
    stroke-width: 3;
  }
</style>
