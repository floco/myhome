<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { CostCategory } from "../settingsStore.svelte";

  interface Props {
    categories: CostCategory[];
    viewport: ViewportState;
    active: boolean;
    width: number;
    height: number;
    onclick: (categoryId: string) => void;
    ondragend: (categoryId: string, worldPos: { x: number; y: number }) => void;
  }

  let { categories, viewport, active, width, height, onclick, ondragend }: Props = $props();

  let dragId = $state<string | null>(null);
  let dragStartScreen = $state({ x: 0, y: 0 });
  let dragStartWorld = $state({ x: 0, y: 0 });
  let dragOffsetScreen = $state({ x: 0, y: 0 });

  function pinScreen(cat: CostCategory): { x: number; y: number } | null {
    if (!cat.placement) return null;
    const base = worldToScreen(cat.placement.position, viewport);
    if (dragId === cat.id) {
      return { x: base.x + dragOffsetScreen.x, y: base.y + dragOffsetScreen.y };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, cat: CostCategory): void {
    if (!active || !cat.placement) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = cat.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = { x: cat.placement.position.x, y: cat.placement.position.y };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = { x: e.clientX - dragStartScreen.x, y: e.clientY - dragStartScreen.y };
  }

  function handlePointerUp(e: PointerEvent, cat: CostCategory): void {
    if (!dragId || dragId !== cat.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      ondragend(cat.id, { x: dragStartWorld.x + dx / viewport.zoom, y: dragStartWorld.y + dy / viewport.zoom });
    } else {
      onclick(cat.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const placedCategories = $derived(categories.filter(c => c.placement !== null));
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));

  function groupStyle(cat: CostCategory): string {
    const pe = active ? "all" : "none";
    const cursor = active ? (dragId === cat.id ? "grabbing" : "grab") : "default";
    return `pointer-events:${pe};cursor:${cursor}`;
  }
</script>

<svelte:window onpointermove={handlePointerMove} />

<svg {width} {height} style="position:absolute;top:0;left:0;pointer-events:none;overflow:visible">
  {#each placedCategories as cat (cat.id)}
    {@const sp = pinScreen(cat)}
    {#if sp}
      <g transform="translate({sp.x},{sp.y}) scale({badgeScale})" style={groupStyle(cat)}
         onpointerdown={(e) => handlePointerDown(e, cat)}
         onpointerup={(e) => handlePointerUp(e, cat)}>
        <text text-anchor="middle" dominant-baseline="central" font-size="26"
          style="filter:drop-shadow(0 1px 4px #0008);user-select:none;pointer-events:none"
        >{cat.emoji}</text>
        <rect x="-30" y="15" width="60" height="13" rx="3" fill="#1a1a3a" fill-opacity="0.85" stroke="#5566cc44" stroke-width="1" />
        <text x="0" y="22" text-anchor="middle" font-size="9" fill="#99a"
          style="pointer-events:none;user-select:none"
        >{cat.name.length > 14 ? cat.name.slice(0, 13) + "…" : cat.name}</text>
      </g>
    {/if}
  {/each}
</svg>
