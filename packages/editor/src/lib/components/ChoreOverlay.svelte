<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { Chore, Assignment, Position } from "../choreStore.svelte";

  interface Props {
    chores: Chore[];
    assignments: Assignment[];
    viewport: ViewportState;
    choreMode: boolean;
    width: number;
    height: number;
    onclick: (assignmentId: string) => void;
    ondragend: (assignmentId: string, worldPos: Position) => void;
  }

  let { chores, assignments, viewport, choreMode, width, height, onclick, ondragend }: Props = $props();

  const R = 18;
  const C = 2 * Math.PI * R;

  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));

  function findChore(choreId: string): Chore | undefined {
    return chores.find((c) => c.id === choreId);
  }

  function getProgress(assignment: Assignment, chore: Chore): number {
    const now = Date.now();
    const due = new Date(assignment.nextDueDate).getTime();
    const periodMs = chore.periodDays * 86400 * 1000;
    return Math.max(0, Math.min(1, (due - now) / periodMs));
  }

  function getColor(pct: number): string {
    if (pct > 0.5) return "#4caf50";
    if (pct > 0.25) return "#ff9800";
    return "#f44336";
  }

  let dragId = $state<string | null>(null);
  let dragStartScreen = $state<Position>({ x: 0, y: 0 });
  let dragStartWorld = $state<Position>({ x: 0, y: 0 });
  let dragOffsetScreen = $state<Position>({ x: 0, y: 0 });

  function badgeScreen(a: Assignment): Position | null {
    if (!a.position) return null;
    const base = worldToScreen(a.position, viewport);
    if (dragId === a.id) {
      return { x: base.x + dragOffsetScreen.x, y: base.y + dragOffsetScreen.y };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, a: Assignment): void {
    if (!choreMode || !a.position) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = a.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = { x: a.position.x, y: a.position.y };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = { x: e.clientX - dragStartScreen.x, y: e.clientY - dragStartScreen.y };
  }

  function handlePointerUp(e: PointerEvent, a: Assignment): void {
    if (!dragId || dragId !== a.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      const worldPos: Position = {
        x: dragStartWorld.x + dx / viewport.zoom,
        y: dragStartWorld.y + dy / viewport.zoom,
      };
      ondragend(a.id, worldPos);
    } else {
      onclick(a.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const roomAssignments = $derived(
    assignments.filter((a) => a.roomId !== null && a.position !== null)
  );
</script>

<svelte:window onpointermove={handlePointerMove} />

<svg
  {width}
  {height}
  style="position:absolute;top:0;left:0;pointer-events:none;overflow:visible"
>
  {#each roomAssignments as a (a.id)}
    {@const chore = findChore(a.choreId)}
    {#if chore}
      {@const sp = badgeScreen(a)}
      {#if sp}
        {@const pct = getProgress(a, chore)}
        {@const color = getColor(pct)}
        {@const dashFill = pct * C}
        <g
          transform="translate({sp.x},{sp.y}) scale({badgeScale})"
          style="pointer-events:{choreMode ? 'all' : 'none'};cursor:{choreMode ? (dragId === a.id ? 'grabbing' : 'grab') : 'default'}"
          onpointerdown={(e) => handlePointerDown(e, a)}
          onpointerup={(e) => handlePointerUp(e, a)}
        >
          <circle r={R + 3} fill="#1a1a2e" opacity="0.75"/>
          <circle r={R} fill="none" stroke="#3a3a3a" stroke-width="5"/>
          <circle r={R} fill="none" stroke={color} stroke-width="5"
            stroke-dasharray="{dashFill} {C}" stroke-linecap="round"
            transform="rotate(-90 0 0)"/>
          <text
            text-anchor="middle"
            dominant-baseline="central"
            font-size="13"
            style="user-select:none;pointer-events:none"
          >{chore.emoji}</text>
        </g>
      {/if}
    {/if}
  {/each}
</svg>
