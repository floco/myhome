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
  }: {
    wall: Wall;
    opening: Opening;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    onselect?: (id: string) => void;
  } = $props();

  const dir = $derived.by(() => {
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const length = Math.hypot(dx, dy);
    if (length < 1e-9) return { x: 1, y: 0, length: 0 };
    return { x: dx / length, y: dy / length, length };
  });

  const wp1 = $derived({
    x: wall.start.x + dir.x * opening.offset,
    y: wall.start.y + dir.y * opening.offset,
  });
  const wp2 = $derived({
    x: wall.start.x + dir.x * (opening.offset + opening.width),
    y: wall.start.y + dir.y * (opening.offset + opening.width),
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
    const swing = opening.swing ?? "left-in";
    const isLeft = swing === "left-in" || swing === "left-out";
    const isIn = swing === "left-in" || swing === "right-in";
    const perpSign = isIn ? -1 : 1;
    const perpX = perpSign * -dir.y;
    const perpY = perpSign * dir.x;
    const hingeWorld = isLeft ? wp1 : wp2;
    const otherWorld = isLeft ? wp2 : wp1;
    const openEndWorld = {
      x: hingeWorld.x + perpX * opening.width,
      y: hingeWorld.y + perpY * opening.width,
    };
    const hinge = worldToScreen(hingeWorld, viewport);
    const other = worldToScreen(otherWorld, viewport);
    const openEnd = worldToScreen(openEndWorld, viewport);
    const radius = opening.width * viewport.zoom;
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
{/if}

<style>
  .selected-gap {
    fill: rgba(0, 128, 255, 0.15);
  }
</style>
