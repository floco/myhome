<script lang="ts">
  import type { createChoreStore, Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    draggingChoreId: string | null;
    onDragStart: (choreId: string) => void;
    onDragEnd: () => void;
  }

  let { store, draggingChoreId, onDragStart, onDragEnd }: Props = $props();

  function displayName(chore: Chore): string {
    let name = chore.name.trim();
    if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
    return name;
  }

  const houseChores = $derived(
    store.houseAssignments().map((a) => ({
      assignment: a,
      chore: store.chores.find((c) => c.id === a.choreId),
    })).filter((x): x is { assignment: typeof x.assignment; chore: Chore } => x.chore !== undefined)
  );
</script>

<div class="panel">
  <div class="panel-header">Chores <span class="hint">— drag to room</span></div>

  {#if houseChores.length > 0}
    <div class="section">
      <div class="section-title">🏠 Whole house</div>
      {#each houseChores as { assignment, chore }}
        <div class="chore-row">
          <span>{chore.emoji}</span>
          <span class="chore-name">{displayName(chore)}</span>
          <button onclick={() => store.completeAssignment(assignment.id)}>✓</button>
          <button onclick={() => store.deleteAssignment(assignment.id)}>✕</button>
        </div>
      {/each}
    </div>
  {/if}

  <div class="section chores-list">
    <div class="section-title">Chores ({store.chores.length})</div>
    {#each store.chores as chore (chore.id)}
      {@const proxyAssignment = store.assignments.find(a => a.choreId === chore.id && a.roomId !== null) ?? { id: '', choreId: chore.id, roomId: null, position: null, nextDueDate: chore.nextDueDate }}
      {@const pct = store.getProgress(proxyAssignment, chore)}
      {@const color = store.getColor(pct)}
      <div
        class="chore-item"
        class:dragging={draggingChoreId === chore.id}
        draggable={true}
        ondragstart={(e) => { e.dataTransfer?.setData("choreId", chore.id); onDragStart(chore.id); }}
        ondragend={() => onDragEnd()}
      >
        <svg width="22" height="22" viewBox="-11 -11 22 22" style="flex-shrink:0">
          <circle r="9" fill="none" stroke="#3a3a3a" stroke-width="3"/>
          <circle r="9" fill="none" stroke={color} stroke-width="3"
            stroke-dasharray="{pct * 56.5} 56.5" stroke-linecap="round"
            transform="rotate(-90 0 0)"/>
          <text text-anchor="middle" dominant-baseline="central" font-size="8">{chore.emoji}</text>
        </svg>
        <div class="chore-info">
          <span class="chore-name">{displayName(chore)}</span>
          <span class="chore-sub">{scheduleLabel(chore)}</span>
        </div>
        <button
          class="house-btn"
          title="Assign to whole house"
          onclick={() => store.createAssignment({ choreId: chore.id, roomId: null, position: null, nextDueDate: chore.nextDueDate })}
        >🏠</button>
      </div>
    {/each}
  </div>
</div>

<style>
  .panel { width: 260px; height: 100%; background: #1e1e2e; border-left: 1px solid #333; overflow-y: auto; z-index: 10; display: flex; flex-direction: column; font-size: 12px; color: #ccc; flex-shrink: 0; }
  .panel-header { padding: 8px 12px; font-size: 13px; font-weight: 600; color: #eee; border-bottom: 1px solid #333; background: #252535; }
  .hint { font-size: 10px; color: #666; font-weight: normal; }
  .section { padding: 8px 12px; border-bottom: 1px solid #2a2a3a; }
  .section-title { font-size: 10px; text-transform: uppercase; color: #666; margin-bottom: 6px; }
  .chores-list { flex: 1; }
  .chore-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; }
  .chore-item { display: flex; align-items: center; gap: 6px; padding: 5px 4px; border-radius: 4px; cursor: grab; user-select: none; }
  .chore-item:hover { background: #2a2a4a; }
  .chore-item.dragging { opacity: 0.5; }
  .chore-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .chore-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chore-sub { font-size: 10px; color: #666; }
  button { padding: 4px 8px; border: none; border-radius: 3px; background: #3a3a5a; color: #ccc; cursor: pointer; font-size: 12px; min-height: 30px; touch-action: manipulation; }
  button:hover { background: #4a4a6a; }
  .house-btn { flex-shrink: 0; }
</style>
