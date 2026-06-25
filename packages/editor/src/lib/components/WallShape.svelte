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

  const thickness = $derived(wall.thickness ?? 0.1);

  const corners = $derived.by(() => {
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const len = Math.hypot(dx, dy);
    if (len < 1e-9) return [];
    const ux = dx / len;
    const uy = dy / len;
    const px = -uy * (thickness / 2);
    const py = ux * (thickness / 2);
    const worldCorners = [
      { x: wall.start.x + px, y: wall.start.y + py },
      { x: wall.end.x + px, y: wall.end.y + py },
      { x: wall.end.x - px, y: wall.end.y - py },
      { x: wall.start.x - px, y: wall.start.y - py },
    ];
    return worldCorners.map((p) => worldToScreen(p, viewport));
  });

  const points = $derived(corners.map((c) => `${c.x},${c.y}`).join(" "));

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
    event.stopPropagation();
    onselect?.(wall.id);
  }
</script>

{#if corners.length > 0}
  <polygon {points} class="wall" class:selected onclick={handleClick} role="button" tabindex="0" />
{/if}

<style>
  .wall {
    fill: var(--canvas-wall);
    stroke: var(--canvas-wall);
    cursor: pointer;
  }
  .wall.selected {
    fill: var(--canvas-wall-selected);
    stroke: var(--canvas-wall-selected);
  }
</style>
