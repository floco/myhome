<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import Card from "./ui/Card.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;

  interface Props {
    worksStore: WorksStore;
    onnavigate: () => void;
  }
  let { worksStore, onnavigate }: Props = $props();

  const plannedCount = $derived(worksStore.works.filter((w) => w.status === "planned").length);
  const inProgressCount = $derived(worksStore.works.filter((w) => w.status === "in_progress").length);
  const doneCount = $derived(worksStore.works.filter((w) => w.status === "done").length);
  const totalCost = $derived(worksStore.works.reduce((sum, w) => sum + (w.totalCost ?? 0), 0));

  const recentWorks = $derived(
    [...worksStore.works].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).slice(0, 5)
  );

  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

  function statusLabel(status: Work["status"]): string {
    if (status === "planned") return "Planned";
    if (status === "in_progress") return "In progress";
    return "Done";
  }
</script>

<div class="widget" role="button" tabindex="0" onclick={onnavigate} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onnavigate(); } }}>
  <Card>
    <div class="header">
      <h3>🔧 Works</h3>
      <span class="sub">{totalCost.toLocaleString(undefined, { maximumFractionDigits: 0 })} € total</span>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-value">{plannedCount}</div><div class="stat-label">Planned</div></div>
      <div class="stat"><div class="stat-value">{inProgressCount}</div><div class="stat-label">In progress</div></div>
      <div class="stat"><div class="stat-value">{doneCount}</div><div class="stat-label">Done</div></div>
    </div>
    {#if recentWorks.length === 0}
      <p class="empty">No works logged yet.</p>
    {:else}
      <ul class="list">
        {#each recentWorks as work (work.id)}
          <li>
            <span class="title">{work.title}</span>
            <span class="status status-{work.status}">{statusLabel(work.status)}</span>
            <span class="date">{formatDate(work.date)}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-3); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .sub { font-size: 11px; color: var(--text-faint); }
  .stats { display: flex; gap: var(--space-2); margin-bottom: var(--space-3); }
  .stat { flex: 1; text-align: center; }
  .stat-value { font-size: 18px; font-weight: 700; color: var(--text); }
  .stat-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; }
  .list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .list li { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
  .title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); font-weight: 500; }
  .status { font-size: 10px; padding: 2px 6px; border-radius: var(--radius-pill); background: var(--surface-alt); white-space: nowrap; }
  .status-done { color: var(--success); }
  .status-in_progress { color: var(--warning); }
  .status-planned { color: var(--text-faint); }
  .date { font-size: 11px; color: var(--text-faint); white-space: nowrap; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
