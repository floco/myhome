<script lang="ts">
  import type { Wall } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";

  let {
    wall,
    viewport,
    tool = "select",
    selected = false,
    onselect,
  }: {
    wall: Wall;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    onselect?: (id: string) => void;
  } = $props();

  const startScreen = $derived(worldToScreen(wall.start, viewport));
  const endScreen = $derived(worldToScreen(wall.end, viewport));
  const x1 = $derived(startScreen.x);
  const y1 = $derived(startScreen.y);
  const x2 = $derived(endScreen.x);
  const y2 = $derived(endScreen.y);

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
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
