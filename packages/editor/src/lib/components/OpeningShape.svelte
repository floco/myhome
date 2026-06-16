<script lang="ts">
  import type { Wall, Opening } from "@myhome/geometry";
  import { chooseSweepFlag } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte.ts";
  import type { ToolType } from "../toolStore.svelte";

  let {
    wall,
    opening,
    viewport,
    tool = "select",
    selected = false,
    onselect,
    ondraghandlestart,
  }: {
    wall: Wall;
    opening: Opening;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    onselect?: (id: string) => void;
    ondraghandlestart?: (openingId: string, side: "start" | "end", event: MouseEvent) => void;
  } = $props();

  const dir = $derived.by(() => {
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const length = Math.hypot(dx, dy);
    if (length < 1e-9) return { x: 1, y: 0, length: 0 };
    return { x: dx / length, y: dy / length, length };
  });

  const clampedFrom = $derived(Math.max(0, Math.min(dir.length, opening.offset)));
  const clampedTo = $derived(Math.max(clampedFrom, Math.min(dir.length, opening.offset + opening.width)));

  const wp1 = $derived({
    x: wall.start.x + dir.x * clampedFrom,
    y: wall.start.y + dir.y * clampedFrom,
  });
  const wp2 = $derived({
    x: wall.start.x + dir.x * clampedTo,
    y: wall.start.y + dir.y * clampedTo,
  });

  const sp1 = $derived(worldToScreen(wp1, viewport));
  const sp2 = $derived(worldToScreen(wp2, viewport));

  const thickness = $derived(wall.thickness ?? 0.1);

  const gapPoints = $derived.by(() => {
    const perpX = -dir.y * (thickness / 2);
    const perpY = dir.x * (thickness / 2);
    const c1 = worldToScreen({ x: wp1.x + perpX, y: wp1.y + perpY }, viewport);
    const c2 = worldToScreen({ x: wp2.x + perpX, y: wp2.y + perpY }, viewport);
    const c3 = worldToScreen({ x: wp2.x - perpX, y: wp2.y - perpY }, viewport);
    const c4 = worldToScreen({ x: wp1.x - perpX, y: wp1.y - perpY }, viewport);
    return `${c1.x},${c1.y} ${c2.x},${c2.y} ${c3.x},${c3.y} ${c4.x},${c4.y}`;
  });

  const doorData = $derived.by(() => {
    if (opening.type !== "door") return null;
    const from = Math.max(0, Math.min(dir.length, opening.offset));
    const to = Math.max(from, Math.min(dir.length, opening.offset + opening.width));
    const width = to - from;
    if (width < 1e-9) return null;
    const swing = opening.swing ?? "left-in";
    const isLeft = swing === "left-in" || swing === "left-out";
    const isIn = swing === "left-in" || swing === "right-in";
    const perpX = isIn ? -dir.y : dir.y;
    const perpY = isIn ? dir.x : -dir.x;
    const hingeWorld = isLeft ? wp1 : wp2;
    const otherWorld = isLeft ? wp2 : wp1;
    const openEndWorld = {
      x: hingeWorld.x + perpX * width,
      y: hingeWorld.y + perpY * width,
    };
    const hinge = worldToScreen(hingeWorld, viewport);
    const other = worldToScreen(otherWorld, viewport);
    const openEnd = worldToScreen(openEndWorld, viewport);
    const radius = width * viewport.zoom;
    const sweep = chooseSweepFlag(other, openEnd, radius, hinge);
    return { hinge, other, openEnd, radius, sweep };
  });

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
    event.stopPropagation();
    onselect?.(opening.id);
  }
</script>

{#if dir.length >= 1e-9}
  <polygon
    points={gapPoints}
    fill="#1c1c1c"
    stroke="none"
    class:selected-gap={selected}
    onclick={handleClick}
    role="button"
    tabindex="0"
  />

  {#if opening.type === "window"}
    <line
      class="window-sym"
      x1={sp1.x}
      y1={sp1.y}
      x2={sp2.x}
      y2={sp2.y}
      stroke={selected ? "#5af" : "#8cf"}
      stroke-width="3"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
  {:else if opening.type === "door" && doorData}
    <line
      class="door-leaf"
      x1={doorData.hinge.x}
      y1={doorData.hinge.y}
      x2={doorData.openEnd.x}
      y2={doorData.openEnd.y}
      stroke={selected ? "#5af" : "#eea"}
      stroke-width="2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
    <path
      class="door-arc"
      d="M {doorData.other.x} {doorData.other.y} A {doorData.radius} {doorData.radius} 0 0 {doorData.sweep} {doorData.openEnd.x} {doorData.openEnd.y}"
      fill="none"
      stroke={selected ? "#5af" : "#eea"}
      stroke-width="1"
      stroke-dasharray="4 2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
  {/if}

  {#if selected}
    <circle
      class="handle"
      cx={sp1.x}
      cy={sp1.y}
      r="5"
      onmousedown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "start", e); }}
      role="button"
      tabindex="0"
    />
    <circle
      class="handle"
      cx={sp2.x}
      cy={sp2.y}
      r="5"
      onmousedown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "end", e); }}
      role="button"
      tabindex="0"
    />
  {/if}
{/if}

<style>
  .selected-gap {
    fill: rgba(0, 128, 255, 0.15);
  }

  .handle {
    fill: #5af;
    stroke: #fff;
    stroke-width: 1.5;
    cursor: ew-resize;
  }
</style>
