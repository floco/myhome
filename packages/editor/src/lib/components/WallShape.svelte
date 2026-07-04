<script lang="ts">
  import type { Wall, Point } from "@myhome/geometry";
  import { computeMiterCorners } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";

  let {
    wall,
    wallAtStart = null,
    wallAtEnd = null,
    viewport,
    tool = "select",
    selected = false,
    onselect,
  }: {
    wall: Wall;
    wallAtStart?: Wall | null;
    wallAtEnd?: Wall | null;
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
    const dirX = dx / len;
    const dirY = dy / len;
    const halfThick = thickness / 2;
    const dir = { x: dirX, y: dirY };
    const px = -dirY * halfThick;
    const py = dirX * halfThick;

    let startTop: Point = { x: wall.start.x + px, y: wall.start.y + py };
    let startBot: Point = { x: wall.start.x - px, y: wall.start.y - py };
    let endTop: Point   = { x: wall.end.x   + px, y: wall.end.y   + py };
    let endBot: Point   = { x: wall.end.x   - px, y: wall.end.y   - py };

    if (wallAtStart) {
      const ndx = wallAtStart.end.x - wallAtStart.start.x;
      const ndy = wallAtStart.end.y - wallAtStart.start.y;
      const nlen = Math.hypot(ndx, ndy);
      if (nlen > 1e-9) {
        const miter = computeMiterCorners(
          wall.start, dir, halfThick,
          { x: ndx / nlen, y: ndy / nlen }, (wallAtStart.thickness ?? 0.1) / 2,
        );
        if (miter) { startTop = miter.plus; startBot = miter.minus; }
      }
    }

    if (wallAtEnd) {
      const ndx = wallAtEnd.end.x - wallAtEnd.start.x;
      const ndy = wallAtEnd.end.y - wallAtEnd.start.y;
      const nlen = Math.hypot(ndx, ndy);
      if (nlen > 1e-9) {
        const miter = computeMiterCorners(
          wall.end, dir, halfThick,
          { x: ndx / nlen, y: ndy / nlen }, (wallAtEnd.thickness ?? 0.1) / 2,
        );
        if (miter) { endTop = miter.plus; endBot = miter.minus; }
      }
    }

    const worldCorners = [startTop, endTop, endBot, startBot];
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
    stroke: none;
    cursor: pointer;
  }
  .wall.selected {
    fill: var(--canvas-wall-selected);
    stroke: none;
  }
</style>
