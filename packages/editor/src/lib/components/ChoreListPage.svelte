<script lang="ts">
  import type { createChoreStore, Chore, Assignment } from "../choreStore.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
  }

  let { store, floorStore }: Props = $props();

  function getRoomName(roomId: string | null): string {
    if (!roomId) return "🏠 Whole house";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || `Room (${floor.name})`;
    }
    return "Unknown room";
  }

  function displayName(chore: Chore): string {
    let name = chore.name.trim();
    if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
    return name;
  }

  function formatDue(iso: string): string {
    if (!iso) return "—";
    const d = new Date(iso);
    const now = new Date();
    const diffDays = Math.round((d.getTime() - now.getTime()) / 86400000);
    if (diffDays < -1) return `${Math.abs(diffDays)}d overdue`;
    if (diffDays === -1) return "Yesterday";
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Tomorrow";
    if (diffDays <= 7) return `In ${diffDays}d`;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  type Row = { assignment: Assignment; chore: Chore; pct: number };

  const rows = $derived(
    store.assignments
      .map((a) => {
        const chore = store.chores.find((c) => c.id === a.choreId);
        if (!chore) return null;
        return { assignment: a, chore, pct: store.getProgress(a, chore) };
      })
      .filter((r): r is Row => r !== null)
      .sort((a, b) => a.pct - b.pct)
  );

  const overdue = $derived(rows.filter((r) => r.pct <= 0.25));
  const ok = $derived(rows.filter((r) => r.pct > 0.25));

  let completing = $state<string | null>(null);

  async function complete(id: string): Promise<void> {
    completing = id;
    await store.completeAssignment(id);
    completing = null;
  }
</script>

<div class="page">
  <header class="page-header">
    <h2>Chore List</h2>
    <span class="count">{rows.length} assignments</span>
  </header>

  <div class="list">
    {#if overdue.length > 0}
      <div class="group-header urgent">Needs attention ({overdue.length})</div>
      {#each overdue as { assignment, chore, pct } (assignment.id)}
        {@const color = store.getColor(pct)}
        <div class="row">
          <span class="emoji">{chore.emoji}</span>
          <span class="name">{displayName(chore)}</span>
          <span class="location">{getRoomName(assignment.roomId)}</span>
          <span class="due" style="color:{color}">{formatDue(assignment.nextDueDate)}</span>
          <button
            class="done-btn"
            disabled={completing === assignment.id}
            onclick={() => complete(assignment.id)}
            title="Mark done"
          >✓</button>
        </div>
      {/each}
    {/if}

    {#if ok.length > 0}
      {#if overdue.length > 0}<div class="group-divider"></div>{/if}
      <div class="group-header">On track ({ok.length})</div>
      {#each ok as { assignment, chore, pct } (assignment.id)}
        {@const color = store.getColor(pct)}
        <div class="row">
          <span class="emoji">{chore.emoji}</span>
          <span class="name">{displayName(chore)}</span>
          <span class="location">{getRoomName(assignment.roomId)}</span>
          <span class="due" style="color:{color}">{formatDue(assignment.nextDueDate)}</span>
          <button
            class="done-btn"
            disabled={completing === assignment.id}
            onclick={() => complete(assignment.id)}
            title="Mark done"
          >✓</button>
        </div>
      {/each}
    {/if}

    {#if rows.length === 0}
      <div class="empty">No chore assignments yet. Go to Management to create chores and assign them to rooms.</div>
    {/if}
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: #1a1a2e; color: #ccc; font-family: sans-serif; }
  .page-header {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; background: #252535; border-bottom: 1px solid #333; flex-shrink: 0;
  }
  .page-header h2 { margin: 0; font-size: 15px; font-weight: 600; color: #eee; }
  .count { font-size: 11px; color: #666; }

  .list { flex: 1; overflow-y: auto; }

  .group-header {
    padding: 8px 16px 4px;
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
    color: #666; background: #1a1a2e; position: sticky; top: 0;
  }
  .group-header.urgent { color: #f44336; }
  .group-divider { height: 8px; background: #1a1a2e; }

  .row {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 16px; border-bottom: 1px solid #22223a;
    font-size: 13px;
  }
  .row:hover { background: #1e1e38; }

  .emoji { font-size: 16px; flex-shrink: 0; width: 22px; text-align: center; }
  .name { flex: 2; min-width: 80px; font-weight: 500; color: #ddd; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .location { flex: 2; min-width: 80px; color: #888; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .due { flex: 1; min-width: 70px; font-size: 12px; text-align: right; white-space: nowrap; }

  .done-btn {
    padding: 4px 10px; border: none; border-radius: 4px;
    background: #2a6; color: #fff; cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0; touch-action: manipulation;
  }
  .done-btn:hover { background: #3b7; }
  .done-btn:disabled { opacity: 0.5; cursor: default; }

  .empty { padding: 40px 20px; text-align: center; color: #555; font-size: 13px; line-height: 1.6; }

  @media (max-width: 500px) {
    .row { flex-wrap: wrap; gap: 6px; }
    .location { flex-basis: 100%; order: 3; }
    .due { text-align: left; }
  }
</style>
