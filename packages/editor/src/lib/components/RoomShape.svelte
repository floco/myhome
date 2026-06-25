<script lang="ts">
  import type { Room } from "@myhome/geometry";
  import { polygonCentroid } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";

  let {
    room,
    viewport,
    tool = "select",
    selected = false,
    onselectroom,
  }: {
    room: Room;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    onselectroom?: (id: string) => void;
  } = $props();

  const screenPoints = $derived.by(() => {
    if (!room.polygon) return [];
    return room.polygon.map((p) => ({
      x: p.x * viewport.zoom + viewport.panX,
      y: p.y * viewport.zoom + viewport.panY,
    }));
  });

  const points = $derived(screenPoints.map((p) => `${p.x},${p.y}`).join(" "));

  const labelPos = $derived.by(() => {
    if (!room.polygon) return { x: 0, y: 0 };
    const c = polygonCentroid(room.polygon);
    return { x: c.x * viewport.zoom + viewport.panX, y: c.y * viewport.zoom + viewport.panY };
  });

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
    event.stopPropagation();
    onselectroom?.(room.id);
  }
</script>

{#if room.polygon}
  <polygon
    {points}
    class="room"
    class:selected
    onclick={handleClick}
    role="button"
    tabindex="0"
  />
  <text
    x={labelPos.x}
    y={labelPos.y}
    class="room-label"
    text-anchor="middle"
    pointer-events="none"
  >
    {room.label || String(room.areaM2) + " m²"}
  </text>
{/if}

<style>
  .room {
    fill: var(--canvas-room-fill);
    fill-opacity: 0.5;
    stroke: none;
    cursor: pointer;
  }
  .room.selected {
    fill: var(--canvas-room-fill-selected);
    fill-opacity: 0.6;
    stroke: var(--canvas-wall-selected);
    stroke-width: 2;
  }
  .room-label {
    fill: var(--canvas-label);
    font-size: 12px;
    dominant-baseline: middle;
    pointer-events: none;
  }
</style>
