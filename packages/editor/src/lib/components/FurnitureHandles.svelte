<script lang="ts">
  import type { FurnitureObject } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte.ts";
  import { worldToScreen } from "../viewportStore.svelte.ts";

  type Corner = "nw" | "ne" | "se" | "sw";

  let {
    object,
    viewport,
    onresizestart,
    onrotatestart,
  }: {
    object: FurnitureObject;
    viewport: ViewportState;
    onresizestart?: (id: string, corner: Corner, e: MouseEvent) => void;
    onrotatestart?: (id: string, e: MouseEvent) => void;
  } = $props();

  const HANDLE_SIZE = 8;
  const ROTATE_OFFSET = 20; // px above top-center

  const cs = $derived(worldToScreen({ x: object.x, y: object.y }, viewport));
  const hw = $derived((object.width  / 2) * viewport.zoom);
  const hh = $derived((object.height / 2) * viewport.zoom);

  // Rotate a screen-space offset by object.rotation
  function rot(dx: number, dy: number): { x: number; y: number } {
    const rad = (object.rotation * Math.PI) / 180;
    const c = Math.cos(rad);
    const s = Math.sin(rad);
    return { x: cs.x + dx * c - dy * s, y: cs.y + dx * s + dy * c };
  }

  const corners = $derived([
    { key: "nw" as Corner, ...rot(-hw, -hh) },
    { key: "ne" as Corner, ...rot( hw, -hh) },
    { key: "se" as Corner, ...rot( hw,  hh) },
    { key: "sw" as Corner, ...rot(-hw,  hh) },
  ]);

  // Rotate handle: top-center then move further "up" along object's local -y axis.
  // The local "up" unit vector in screen space is (+sin θ, -cos θ) for clockwise rotation.
  const rotHandle = $derived((() => {
    const topCenter = rot(0, -hh);
    const rad = (object.rotation * Math.PI) / 180;
    return {
      x: topCenter.x + Math.sin(rad) * ROTATE_OFFSET,
      y: topCenter.y - Math.cos(rad) * ROTATE_OFFSET,
    };
  })());

  function handleCornerDown(corner: Corner, e: MouseEvent) {
    e.stopPropagation();
    onresizestart?.(object.id, corner, e);
  }

  function handleRotateDown(e: MouseEvent) {
    e.stopPropagation();
    onrotatestart?.(object.id, e);
  }
</script>

{#each corners as c}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <rect
    class="corner-handle"
    x={c.x - HANDLE_SIZE / 2}
    y={c.y - HANDLE_SIZE / 2}
    width={HANDLE_SIZE}
    height={HANDLE_SIZE}
    onmousedown={(e) => handleCornerDown(c.key, e)}
  />
{/each}

<!-- svelte-ignore a11y_no_static_element_interactions -->
<circle
  class="rotate-handle"
  cx={rotHandle.x}
  cy={rotHandle.y}
  r={HANDLE_SIZE / 2 + 2}
  onmousedown={handleRotateDown}
><title>Rotate</title></circle>

<style>
  .corner-handle {
    fill: white;
    stroke: #1a73e8;
    stroke-width: 1.5;
    cursor: nwse-resize;
    rx: 1;
  }

  .rotate-handle {
    fill: #1a73e8;
    stroke: white;
    stroke-width: 1.5;
    cursor: alias;
  }
</style>
