<script lang="ts">
  import type { Room } from "@myhome/geometry";
  import { polygonCentroid } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte";

  let { room, viewport }: { room: Room; viewport: ViewportState } = $props();

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
</script>

{#if room.polygon}
  <polygon {points} class="room" />
  <text x={labelPos.x} y={labelPos.y} class="room-label" text-anchor="middle">
    {room.areaM2} m²
  </text>
{/if}

<style>
  .room {
    fill: #3a5a3a;
    fill-opacity: 0.5;
    stroke: none;
  }
  .room-label {
    fill: #cde;
    font-size: 12px;
    dominant-baseline: middle;
  }
</style>
