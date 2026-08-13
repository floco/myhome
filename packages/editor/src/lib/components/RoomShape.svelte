<script lang="ts">
  import type { Room } from "@myhome/geometry";
  import { computeLabelPosition, roomContainsOtherRooms } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";

  let {
    room,
    allRooms,
    viewport,
    tool = "select",
    selected = false,
    onselectroom,
  }: {
    room: Room;
    allRooms: Room[];
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

  const labelWorldPos = $derived.by(() => {
    if (!room.polygon) return { x: 0, y: 0 };
    return computeLabelPosition(room, allRooms);
  });

  const labelPos = $derived.by(() => {
    const c = labelWorldPos;
    return { x: c.x * viewport.zoom + viewport.panX, y: c.y * viewport.zoom + viewport.panY };
  });

  // A room whose polygon substantially contains other rooms (e.g. a garden
  // boundary with a shed drawn inside it) overlaps its children's fill, so
  // clicking anywhere in that fill would unpredictably steal clicks meant
  // for the nested room underneath. Restrict such a room's click target to
  // its label instead of its whole fill.
  const isContainerZone = $derived.by(() => (room.polygon ? roomContainsOtherRooms(room, allRooms) : false));

  const labelHitWidth = $derived(Math.max(32, (room.label || String(room.areaM2) + " m²").length * 7 + 16));

  function handleClick(event: MouseEvent): void {
    if (tool !== "select") return;
    // The polygon stays focusable even when it's a container zone (see
    // .non-interactive below); guard here so keyboard activation can't
    // bypass the pointer-events restriction.
    if (isContainerZone) return;
    event.stopPropagation();
    onselectroom?.(room.id);
  }

  function handleLabelClick(event: MouseEvent): void {
    if (tool !== "select") return;
    event.stopPropagation();
    onselectroom?.(room.id);
  }

  function handleLabelKeydown(event: KeyboardEvent): void {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    handleLabelClick(event as unknown as MouseEvent);
  }
</script>

{#if room.polygon}
  <polygon
    {points}
    class="room"
    class:selected
    class:non-interactive={isContainerZone}
    onclick={handleClick}
    role="button"
    tabindex="0"
  />
  {#if isContainerZone}
    <rect
      x={labelPos.x - labelHitWidth / 2}
      y={labelPos.y - 12}
      width={labelHitWidth}
      height="24"
      class="room-label-hit"
      class:selected
      onclick={handleLabelClick}
      onkeydown={handleLabelKeydown}
      role="button"
      tabindex="0"
    />
  {/if}
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
  .room.non-interactive {
    pointer-events: none;
  }
  .room-label {
    fill: var(--canvas-label);
    font-size: 12px;
    dominant-baseline: middle;
    pointer-events: none;
  }
  .room-label-hit {
    fill: transparent;
    cursor: pointer;
  }
  .room-label-hit.selected {
    fill: var(--canvas-room-fill-selected);
    fill-opacity: 0.6;
  }
</style>
