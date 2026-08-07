<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Wall, Opening } from "@myhome/geometry";
  import { chooseSweepFlag } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte.ts";
  import type { ToolType } from "../toolStore.svelte";
  import type { HaEntityState } from "../haStateStore.svelte";

  let {
    wall,
    opening,
    viewport,
    tool = "select",
    selected = false,
    haLayerActive = false,
    haState = null,
    shutterState = null,
    onselect,
    ondraghandlestart,
  }: {
    wall: Wall;
    opening: Opening;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    haLayerActive?: boolean;
    haState?: HaEntityState | null;
    shutterState?: HaEntityState | null;
    onselect?: (id: string) => void;
    ondraghandlestart?: (openingId: string, side: "start" | "end", event: PointerEvent) => void;
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

  const sensorStatus = $derived.by((): "open" | "closed" | "unavailable" | null => {
    if (!haLayerActive || !opening.haEntityId) return null;
    if (!haState || haState.state === "unavailable" || haState.state === "unknown") return "unavailable";
    return haState.state === "on" ? "open" : "closed";
  });

  const strokeColor = $derived.by(() => {
    if (selected) return "var(--canvas-wall-selected)";
    if (sensorStatus === "open") return "var(--canvas-opening-open)";
    if (sensorStatus === "unavailable") return "var(--canvas-opening-unavailable)";
    return opening.type === "window" ? "var(--canvas-opening-window)" : "var(--canvas-opening-door)";
  });

  const shutterClosedFraction = $derived.by(() => {
    if (!haLayerActive || opening.type !== "window" || !opening.hasShutter || !shutterState) return 0;
    const pos = shutterState.attributes?.current_position;
    if (typeof pos === "number") return Math.max(0, Math.min(1, (100 - pos) / 100));
    return shutterState.state === "closed" ? 1 : 0;
  });

  const shutterOverlayPoints = $derived.by(() => {
    if (shutterClosedFraction <= 0) return null;
    const closedTo = clampedFrom + (clampedTo - clampedFrom) * shutterClosedFraction;
    const perpX = -dir.y * (thickness / 2);
    const perpY = dir.x * (thickness / 2);
    const startWorld = { x: wall.start.x + dir.x * clampedFrom, y: wall.start.y + dir.y * clampedFrom };
    const endWorld = { x: wall.start.x + dir.x * closedTo, y: wall.start.y + dir.y * closedTo };
    const c1 = worldToScreen({ x: startWorld.x + perpX, y: startWorld.y + perpY }, viewport);
    const c2 = worldToScreen({ x: endWorld.x + perpX, y: endWorld.y + perpY }, viewport);
    const c3 = worldToScreen({ x: endWorld.x - perpX, y: endWorld.y - perpY }, viewport);
    const c4 = worldToScreen({ x: startWorld.x - perpX, y: startWorld.y - perpY }, viewport);
    return `${c1.x},${c1.y} ${c2.x},${c2.y} ${c3.x},${c3.y} ${c4.x},${c4.y}`;
  });

  const windowGlazingLines = $derived.by(() => {
    if (opening.type !== "window" || dir.length < 1e-9) return null;
    const perpIn = { x: -dir.y, y: dir.x };
    const perpOut = { x: dir.y, y: -dir.x };
    const side = opening.windowSide ?? "in";
    const perp = side === "out" ? perpOut : perpIn;
    const majorOffset = thickness * 0.3;
    const minorOffset = thickness * 0.1;
    const offsetLine = (mag: number) => {
      const a = { x: wp1.x + perp.x * mag, y: wp1.y + perp.y * mag };
      const b = { x: wp2.x + perp.x * mag, y: wp2.y + perp.y * mag };
      return { p1: worldToScreen(a, viewport), p2: worldToScreen(b, viewport) };
    };
    return { major: offsetLine(majorOffset), minor: offsetLine(minorOffset) };
  });

  const gapPoints = $derived.by(() => {
    const perpX = -dir.y * (thickness / 2);
    const perpY = dir.x * (thickness / 2);
    const c1 = worldToScreen({ x: wp1.x + perpX, y: wp1.y + perpY }, viewport);
    const c2 = worldToScreen({ x: wp2.x + perpX, y: wp2.y + perpY }, viewport);
    const c3 = worldToScreen({ x: wp2.x - perpX, y: wp2.y - perpY }, viewport);
    const c4 = worldToScreen({ x: wp1.x - perpX, y: wp1.y - perpY }, viewport);
    return `${c1.x},${c1.y} ${c2.x},${c2.y} ${c3.x},${c3.y} ${c4.x},${c4.y}`;
  });

  const doorKind = $derived.by(() => opening.type === "door" ? (opening.doorKind ?? "hinged") : "hinged");

  const hingedOrSwingingData = $derived.by(() => {
    if (opening.type !== "door" || (doorKind !== "hinged" && doorKind !== "swinging")) return null;
    const width = clampedTo - clampedFrom;
    if (width < 1e-9) return null;
    const swing = opening.swing ?? "left-in";
    const isLeft = swing === "left-in" || swing === "left-out";
    const hingeWorld = isLeft ? wp1 : wp2;
    const otherWorld = isLeft ? wp2 : wp1;
    const other = worldToScreen(otherWorld, viewport);
    const radius = width * viewport.zoom;
    const perpIn = { x: -dir.y, y: dir.x };
    const perpOut = { x: dir.y, y: -dir.x };

    const variant = (perp: { x: number; y: number }) => {
      const openEndWorld = { x: hingeWorld.x + perp.x * width, y: hingeWorld.y + perp.y * width };
      const hinge = worldToScreen(hingeWorld, viewport);
      const openEnd = worldToScreen(openEndWorld, viewport);
      const sweep = chooseSweepFlag(other, openEnd, radius, hinge);
      return { hinge, other, openEnd, radius, sweep };
    };

    if (doorKind === "swinging") {
      return { variants: [variant(perpIn), variant(perpOut)] };
    }
    const isIn = swing === "left-in" || swing === "right-in";
    return { variants: [variant(isIn ? perpIn : perpOut)] };
  });

  const slidingBarData = $derived.by(() => {
    if (opening.type !== "door" || doorKind !== "sliding" || dir.length < 1e-9) return null;
    const perpOut = { x: dir.y, y: -dir.x };
    const mag = (thickness / 2) * 0.5;
    const a = { x: wp1.x + perpOut.x * mag, y: wp1.y + perpOut.y * mag };
    const b = { x: wp2.x + perpOut.x * mag, y: wp2.y + perpOut.y * mag };
    return { p1: worldToScreen(a, viewport), p2: worldToScreen(b, viewport) };
  });

  const garageTicksData = $derived.by(() => {
    if (opening.type !== "door" || doorKind !== "garage" || dir.length < 1e-9) return null;
    const tickCount = 5;
    const halfThick = thickness / 2;
    const perpFull = { x: -dir.y * halfThick, y: dir.x * halfThick };
    const ticks: { p1: { x: number; y: number }; p2: { x: number; y: number } }[] = [];
    for (let i = 0; i < tickCount; i++) {
      const t = i / (tickCount - 1);
      const cx = wp1.x + (wp2.x - wp1.x) * t;
      const cy = wp1.y + (wp2.y - wp1.y) * t;
      ticks.push({
        p1: worldToScreen({ x: cx + perpFull.x, y: cy + perpFull.y }, viewport),
        p2: worldToScreen({ x: cx - perpFull.x, y: cy - perpFull.y }, viewport),
      });
    }
    return ticks;
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
    fill="var(--canvas-bg)"
    stroke="none"
    class:selected-gap={selected}
    onclick={handleClick}
    role="button"
    tabindex="0"
  />

  {#if opening.type === "window" && windowGlazingLines}
    <line
      class="window-sym"
      x1={windowGlazingLines.major.p1.x}
      y1={windowGlazingLines.major.p1.y}
      x2={windowGlazingLines.major.p2.x}
      y2={windowGlazingLines.major.p2.y}
      stroke={strokeColor}
      stroke-width="3"
      onclick={handleClick}
      role="button"
      tabindex="0"
    >
      {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
    </line>
    <line
      class="window-sym"
      x1={windowGlazingLines.minor.p1.x}
      y1={windowGlazingLines.minor.p1.y}
      x2={windowGlazingLines.minor.p2.x}
      y2={windowGlazingLines.minor.p2.y}
      stroke={strokeColor}
      stroke-width="1.5"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
    {#if shutterOverlayPoints}
      <polygon points={shutterOverlayPoints} fill="var(--canvas-shutter-fill)" class="shutter-overlay" />
    {/if}
  {:else if opening.type === "door" && hingedOrSwingingData}
    {#each hingedOrSwingingData.variants as v, i (i)}
      <line
        class="door-leaf"
        x1={v.hinge.x}
        y1={v.hinge.y}
        x2={v.openEnd.x}
        y2={v.openEnd.y}
        stroke={strokeColor}
        stroke-width="2"
        onclick={handleClick}
        role="button"
        tabindex="0"
      >
        {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
      </line>
      <path
        class="door-arc"
        d="M {v.other.x} {v.other.y} A {v.radius} {v.radius} 0 0 {v.sweep} {v.openEnd.x} {v.openEnd.y}"
        fill="none"
        stroke={strokeColor}
        stroke-width="1"
        stroke-dasharray="4 2"
        onclick={handleClick}
        role="button"
        tabindex="0"
      />
    {/each}
  {:else if opening.type === "door" && slidingBarData}
    <line
      class="door-sliding"
      x1={slidingBarData.p1.x}
      y1={slidingBarData.p1.y}
      x2={slidingBarData.p2.x}
      y2={slidingBarData.p2.y}
      stroke={strokeColor}
      stroke-width="4"
      onclick={handleClick}
      role="button"
      tabindex="0"
    >
      {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
    </line>
  {:else if opening.type === "door" && garageTicksData}
    {#each garageTicksData as t, i (i)}
      <line
        class="door-garage"
        x1={t.p1.x}
        y1={t.p1.y}
        x2={t.p2.x}
        y2={t.p2.y}
        stroke={strokeColor}
        stroke-width="2"
        onclick={handleClick}
        role="button"
        tabindex="0"
      >
        {#if i === 0 && sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
      </line>
    {/each}
  {/if}

  {#if selected}
    <circle
      class="handle"
      cx={sp1.x}
      cy={sp1.y}
      r="5"
      onpointerdown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "start", e); }}
      role="button"
      tabindex="0"
    />
    <circle
      class="handle"
      cx={sp2.x}
      cy={sp2.y}
      r="5"
      onpointerdown={(e) => { e.stopPropagation(); ondraghandlestart?.(opening.id, "end", e); }}
      role="button"
      tabindex="0"
    />
  {/if}
{/if}

<style>
  .selected-gap {
    fill: var(--canvas-selected-fill);
  }

  .handle {
    fill: var(--canvas-wall-selected);
    stroke: var(--text);
    stroke-width: 1.5;
    cursor: ew-resize;
  }
</style>
