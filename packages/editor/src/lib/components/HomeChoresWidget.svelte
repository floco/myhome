<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createChoreStore } from "../choreStore.svelte.ts";
  import { displayName, formatDue } from "../choreFormat";
  import Card from "./ui/Card.svelte";
  import ChoreRow from "./ChoreRow.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    onnavigate: () => void;
  }
  let { store, onnavigate }: Props = $props();

  interface Row {
    id: string;
    pct: number;
    emoji: string;
    name: string;
    dueLabel: string;
    dueColor: string;
  }

  const rows = $derived(
    store.assignments
      .map((a) => {
        const chore = store.chores.find((c) => c.id === a.choreId);
        if (!chore) return null;
        const pct = store.getProgress(a, chore);
        return {
          id: a.id,
          pct,
          emoji: chore.emoji,
          name: displayName(chore),
          dueLabel: formatDue(a.nextDueDate),
          dueColor: store.getColor(pct),
        } as Row;
      })
      .filter((r): r is Row => r !== null)
      .sort((a, b) => a.pct - b.pct)
  );

  const overdueCount = $derived(rows.filter((r) => r.pct <= 0.25).length);
  const onTrackPct = $derived(
    rows.length > 0 ? Math.round((rows.filter((r) => r.pct > 0.25).length / rows.length) * 100) : 0
  );
  const topFive = $derived(rows.slice(0, 5));
</script>

<div class="widget" role="button" tabindex="0" onclick={onnavigate} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onnavigate(); } }}>
  <Card>
    <div class="header">
      <h3>✅ {$_('common.modules.chores')}</h3>
    </div>
    <div class="stats">
      <div class="stat-item"><b>{rows.length}</b> {$_('home.chores.active')}</div>
      <div class="stat-item overdue"><b>{overdueCount}</b> {$_('chores.page.overdue')}</div>
      <div class="stat-item ontrack"><b>{onTrackPct}%</b> {$_('home.chores.onTrack')}</div>
    </div>
    {#if topFive.length === 0}
      <p class="empty">{$_('home.chores.emptyState')}</p>
    {:else}
      <div class="rows">
        {#each topFive as row (row.id)}
          <ChoreRow
            emoji={row.emoji}
            name={row.name}
            dueLabel={row.dueLabel}
            dueColor={row.dueColor}
            oncomplete={(notes) => store.completeAssignment(row.id, notes)}
          />
        {/each}
      </div>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .stats { display: flex; gap: var(--space-3); font-size: 12px; color: var(--text-muted); margin-bottom: var(--space-2); }
  .stat-item b { color: var(--text); }
  .stat-item.overdue b { color: var(--danger); }
  .stat-item.ontrack b { color: var(--success); }
  .rows { display: flex; flex-direction: column; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
