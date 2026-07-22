<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createChoreStore, Chore, Assignment } from "../choreStore.svelte";
  import { displayName, formatDue } from "../choreFormat";
  import ChoreRow from "./ChoreRow.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
  }

  let { store, floorStore }: Props = $props();

  function getRoomName(roomId: string | null): string {
    if (!roomId) return `🏠 ${$_('chores.list.wholeHouse')}`;
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || $_('chores.list.roomInFloor', { values: { floor: floor.name } });
    }
    return $_('chores.list.unknownRoom');
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
</script>

<div class="page">
  <header class="page-header">
    <h2>{$_('chores.list.title')}</h2>
    <span class="count">{$_('chores.list.assignmentCount', { values: { n: rows.length } })}</span>
  </header>

  <div class="list">
    {#if overdue.length > 0}
      <div class="group-header urgent">{$_('chores.list.needsAttention', { values: { n: overdue.length } })}</div>
      {#each overdue as { assignment, chore, pct } (assignment.id)}
        <ChoreRow
          emoji={chore.emoji}
          name={displayName(chore)}
          location={getRoomName(assignment.roomId)}
          dueLabel={formatDue(assignment.nextDueDate)}
          dueColor={store.getColor(pct)}
          oncomplete={(notes) => store.completeAssignment(assignment.id, notes)}
        />
      {/each}
    {/if}

    {#if ok.length > 0}
      {#if overdue.length > 0}<div class="group-divider"></div>{/if}
      <div class="group-header">{$_('chores.list.onTrack', { values: { n: ok.length } })}</div>
      {#each ok as { assignment, chore, pct } (assignment.id)}
        <ChoreRow
          emoji={chore.emoji}
          name={displayName(chore)}
          location={getRoomName(assignment.roomId)}
          dueLabel={formatDue(assignment.nextDueDate)}
          dueColor={store.getColor(pct)}
          oncomplete={(notes) => store.completeAssignment(assignment.id, notes)}
        />
      {/each}
    {/if}

    {#if rows.length === 0}
      <div class="empty">{$_('chores.list.emptyState')}</div>
    {/if}
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); color: var(--text); font-family: var(--font-sans); }
  .page-header {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .page-header h2 { margin: 0; font-size: 15px; font-weight: 600; color: var(--text); }
  .count { font-size: 11px; color: var(--text-faint); }

  .list { flex: 1; overflow-y: auto; }

  .group-header {
    padding: 8px 16px 4px;
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--text-faint); background: var(--bg); position: sticky; top: 0;
  }
  .group-header.urgent { color: var(--danger); }
  .group-divider { height: 8px; background: var(--bg); }

  .empty { padding: 40px 20px; text-align: center; color: var(--text-faint); font-size: 13px; line-height: 1.6; }
</style>
