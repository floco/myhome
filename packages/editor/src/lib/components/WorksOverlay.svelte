<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    works: Work[];
    settingsStore: SettingsStore;
    viewport: ViewportState;
    active: boolean;
    width: number;
    height: number;
    onclick: (workId: string) => void;
    ondragend: (workId: string, worldPos: { x: number; y: number }) => void;
  }

  let { works, settingsStore, viewport, active, width, height, onclick, ondragend }: Props = $props();

  const categoryMap = $derived(
    new Map(settingsStore.workCategories.map(c => [c.id, c]))
  );

  let dragId = $state<string | null>(null);
  let dragStartScreen = $state({ x: 0, y: 0 });
  let dragStartWorld = $state({ x: 0, y: 0 });
  let dragOffsetScreen = $state({ x: 0, y: 0 });

  function pinScreen(work: Work): { x: number; y: number } | null {
    if (!work.placement) return null;
    const base = worldToScreen(work.placement.position, viewport);
    if (dragId === work.id) {
      return { x: base.x + dragOffsetScreen.x, y: base.y + dragOffsetScreen.y };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, work: Work): void {
    if (!active || !work.placement) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = work.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = { x: work.placement.position.x, y: work.placement.position.y };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = { x: e.clientX - dragStartScreen.x, y: e.clientY - dragStartScreen.y };
  }

  function handlePointerUp(e: PointerEvent, work: Work): void {
    if (!dragId || dragId !== work.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      ondragend(work.id, {
        x: dragStartWorld.x + dx / viewport.zoom,
        y: dragStartWorld.y + dy / viewport.zoom,
      });
    } else {
      onclick(work.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const placedWorks = $derived(works.filter(w => w.placement !== null));
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));

  function groupStyle(work: Work): string {
    const pe = active ? "all" : "none";
    const cursor = active ? (dragId === work.id ? "grabbing" : "grab") : "default";
    return `pointer-events:${pe};cursor:${cursor}`;
  }
</script>

<svelte:window onpointermove={handlePointerMove} />

<svg {width} {height} style="position:absolute;top:0;left:0;pointer-events:none;overflow:visible">
  {#each placedWorks as work (work.id)}
    {@const sp = pinScreen(work)}
    {@const emoji = work.categoryId ? (categoryMap.get(work.categoryId)?.emoji ?? "🔧") : "🔧"}
    {#if sp}
      <g
        transform="translate({sp.x},{sp.y}) scale({badgeScale})"
        style={groupStyle(work)}
        onpointerdown={(e) => handlePointerDown(e, work)}
        onpointerup={(e) => handlePointerUp(e, work)}
      >
        <text
          text-anchor="middle" dominant-baseline="central" font-size="26"
          style="filter:drop-shadow(0 1px 4px #0008);user-select:none;pointer-events:none"
        >{emoji}</text>
        <rect x="-30" y="15" width="60" height="13" rx="3" fill="#1a1a3a" fill-opacity="0.85" stroke="#5566cc44" stroke-width="1" />
        <text x="0" y="22" text-anchor="middle" font-size="9" fill="#99a"
          style="pointer-events:none;user-select:none"
        >{work.title.length > 14 ? work.title.slice(0, 13) + "…" : work.title}</text>
      </g>
    {/if}
  {/each}
</svg>
