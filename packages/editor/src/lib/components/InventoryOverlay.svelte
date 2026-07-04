<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { InventoryItem } from "../inventoryStore.svelte";

  interface Props {
    items: InventoryItem[];
    viewport: ViewportState;
    active: boolean;
    width: number;
    height: number;
    onclick: (itemId: string) => void;
    ondragend: (itemId: string, worldPos: { x: number; y: number }) => void;
  }

  let { items, viewport, active, width, height, onclick, ondragend }: Props =
    $props();

  function glowFilter(item: InventoryItem): string {
    if (!item.warrantyExpiryDate) return "drop-shadow(0 1px 4px #0008)";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    if (expiry < now) return "drop-shadow(0 0 6px #f44336)";
    if (expiry - now <= 30 * 86400 * 1000)
      return "drop-shadow(0 0 6px #ff9800)";
    return "drop-shadow(0 1px 4px #0008)";
  }

  let dragId = $state<string | null>(null);
  let dragStartScreen = $state({ x: 0, y: 0 });
  let dragStartWorld = $state({ x: 0, y: 0 });
  let dragOffsetScreen = $state({ x: 0, y: 0 });

  function pinScreen(item: InventoryItem): { x: number; y: number } | null {
    if (!item.placement) return null;
    const base = worldToScreen(item.placement.position, viewport);
    if (dragId === item.id) {
      return {
        x: base.x + dragOffsetScreen.x,
        y: base.y + dragOffsetScreen.y,
      };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, item: InventoryItem): void {
    if (!active || !item.placement) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = item.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = {
      x: item.placement.position.x,
      y: item.placement.position.y,
    };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = {
      x: e.clientX - dragStartScreen.x,
      y: e.clientY - dragStartScreen.y,
    };
  }

  function handlePointerUp(e: PointerEvent, item: InventoryItem): void {
    if (!dragId || dragId !== item.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      ondragend(item.id, {
        x: dragStartWorld.x + dx / viewport.zoom,
        y: dragStartWorld.y + dy / viewport.zoom,
      });
    } else {
      onclick(item.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const placedItems = $derived(items.filter((i) => i.placement !== null));
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));

  function groupStyle(item: InventoryItem): string {
    const pe = active ? "all" : "none";
    const cursor = active ? (dragId === item.id ? "grabbing" : "grab") : "default";
    return `pointer-events:${pe};cursor:${cursor}`;
  }
</script>

<svelte:window onpointermove={handlePointerMove} />

<svg
  {width}
  {height}
  style="position:absolute;top:0;left:0;pointer-events:none;overflow:visible"
>
  {#each placedItems as item (item.id)}
    {@const sp = pinScreen(item)}
    {#if sp}
      <g
        transform="translate({sp.x},{sp.y}) scale({badgeScale})"
        style={groupStyle(item)}
        onpointerdown={(e) => handlePointerDown(e, item)}
        onpointerup={(e) => handlePointerUp(e, item)}
      >
        <text
          text-anchor="middle"
          dominant-baseline="central"
          font-size="26"
          style="filter:{glowFilter(item)};user-select:none;pointer-events:none"
        >{item.emoji}</text>
        <rect
          x="-30" y="15" width="60" height="13" rx="3"
          fill="#1a1a3a" fill-opacity="0.85" stroke="#5566cc44" stroke-width="1"
        />
        <text
          x="0" y="22"
          text-anchor="middle" font-size="9" fill="#99a"
          style="pointer-events:none;user-select:none"
        >{item.name.length > 14
            ? item.name.slice(0, 13) + "…"
            : item.name}</text>
      </g>
    {/if}
  {/each}
</svg>
