<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { Consumable } from "../consumableStore.svelte";
  import { stockStatus, barFill } from "../consumableStore.svelte";

  interface Props {
    consumables: Consumable[];
    viewport: ViewportState;
    active: boolean;
    width: number;
    height: number;
    onclick: (id: string) => void;
    ondragend: (id: string, worldPos: { x: number; y: number }) => void;
  }

  let { consumables, viewport, active, width, height, onclick, ondragend }: Props = $props();

  // Vertical bar geometry — centered on the badge circle (radius 18)
  const BAR_X = 26;
  const BAR_W = 10;
  const BAR_H = 38;
  const BAR_INNER_H = 34; // fill area (2px padding top+bottom)

  const STATE_COLOR: Record<string, string> = {
    ok: "#4caf50",
    low: "#ff9800",
    empty: "#f44336",
  };

  let dragId = $state<string | null>(null);
  let dragStartScreen = $state({ x: 0, y: 0 });
  let dragStartWorld = $state({ x: 0, y: 0 });
  let dragOffsetScreen = $state({ x: 0, y: 0 });

  function pinScreen(c: Consumable): { x: number; y: number } | null {
    if (!c.placement) return null;
    const base = worldToScreen(c.placement.position, viewport);
    if (dragId === c.id) {
      return { x: base.x + dragOffsetScreen.x, y: base.y + dragOffsetScreen.y };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, c: Consumable): void {
    if (!active || !c.placement) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = c.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = { x: c.placement.position.x, y: c.placement.position.y };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = { x: e.clientX - dragStartScreen.x, y: e.clientY - dragStartScreen.y };
  }

  function handlePointerUp(e: PointerEvent, c: Consumable): void {
    if (!dragId || dragId !== c.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      ondragend(c.id, {
        x: dragStartWorld.x + dx / viewport.zoom,
        y: dragStartWorld.y + dy / viewport.zoom,
      });
    } else {
      onclick(c.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const placedConsumables = $derived(consumables.filter((c) => c.placement !== null));
</script>

<svelte:window onpointermove={handlePointerMove} />

<svg {width} {height} style="position:absolute;top:0;left:0;pointer-events:none;overflow:visible">
  {#each placedConsumables as c (c.id)}
    {@const sp = pinScreen(c)}
    {#if sp}
      {@const st = stockStatus(c)}
      {@const fill = barFill(c)}
      {@const color = STATE_COLOR[st]}
      {@const fillH = Math.round(fill * BAR_INNER_H)}
      {@const fillY = -(BAR_H / 2) + 2 + (BAR_INNER_H - fillH)}
      {@const minY = -(BAR_H / 2) + 2 + Math.round(BAR_INNER_H * (2 / 3))}
      {@const labelQty = c.quantity % 1 === 0 ? String(c.quantity) : c.quantity.toFixed(1)}
      <g
        transform="translate({sp.x},{sp.y})"
        style="pointer-events:{active ? 'all' : 'none'};cursor:{active ? (dragId === c.id ? 'grabbing' : 'grab') : 'default'}"
        onpointerdown={(e) => handlePointerDown(e, c)}
        onpointerup={(e) => handlePointerUp(e, c)}
      >
        <!-- backdrop shadow -->
        <circle r="22" fill="#1a1a2e" opacity="0.8" />
        <!-- inner circle coloured by state -->
        <circle r="18" fill="#1e1e3a" stroke={color} stroke-width={st === "ok" ? 1 : 2} />
        <!-- emoji -->
        <text
          text-anchor="middle"
          dominant-baseline="central"
          font-size="16"
          style="user-select:none;pointer-events:none"
        >{c.emoji}</text>

        <!-- vertical bar track -->
        <rect
          x={BAR_X}
          y={-(BAR_H / 2)}
          width={BAR_W}
          height={BAR_H}
          rx="3"
          fill="#1a1a2e"
          stroke={color}
          stroke-width="1"
        />

        {#if st === "empty"}
          <!-- empty: show ✕ -->
          <text
            x={BAR_X + BAR_W / 2}
            y="0"
            text-anchor="middle"
            dominant-baseline="central"
            font-size="8"
            fill={color}
            style="pointer-events:none;user-select:none"
          >✕</text>
        {:else}
          <!-- fill from bottom -->
          <rect
            x={BAR_X + 1}
            y={fillY}
            width={BAR_W - 2}
            height={fillH}
            rx="2"
            fill={color}
          />
        {/if}

        <!-- min threshold dashed line at 1/3 from bottom -->
        <line
          x1={BAR_X - 2}
          x2={BAR_X + BAR_W + 2}
          y1={minY}
          y2={minY}
          stroke={color}
          stroke-width="1"
          stroke-dasharray="2,1"
          opacity="0.8"
        />

        <!-- quantity label below bar -->
        <text
          x={BAR_X + BAR_W / 2}
          y={BAR_H / 2 + 10}
          text-anchor="middle"
          font-size="8"
          fill={color}
          font-family="sans-serif"
          style="pointer-events:none;user-select:none"
        >{labelQty}</text>
      </g>
    {/if}
  {/each}
</svg>
