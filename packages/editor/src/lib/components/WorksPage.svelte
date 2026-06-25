<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import WorkModal from "./WorkModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: WorksStore;
    settingsStore: SettingsStore;
    onplaceonmap?: (workId: string) => void;
  }

  let { store, settingsStore, onplaceonmap }: Props = $props();

  let modalWork = $state<Work | "create" | null>(null);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let categoryFilter = $state("");

  const categoryMap = $derived(
    new Map(settingsStore.workCategories.map(c => [c.id, c]))
  );
  const supplierMap = $derived(
    new Map(settingsStore.suppliers.map(s => [s.id, s]))
  );

  const filteredWorks = $derived(store.works.filter(w => {
    if (statusFilter && w.status !== statusFilter) return false;
    if (categoryFilter && w.categoryId !== categoryFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!w.title.toLowerCase().includes(q) && !w.description.toLowerCase().includes(q)) return false;
    }
    return true;
  }));

  const totalCost = $derived(
    filteredWorks.reduce((sum, w) => sum + (w.totalCost ?? 0), 0)
  );

  function statusLabel(status: Work["status"]): string {
    if (status === "in_progress") return "In progress";
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  function statusColor(status: Work["status"]): string {
    if (status === "done") return "#33aa66";
    if (status === "in_progress") return "#3388cc";
    return "#cc8833";
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
</script>

<div class="page">
  <div class="toolbar">
    <Input placeholder="🔍 Search…" bind:value={searchQuery} />
    <select class="native-input filter-sel" bind:value={statusFilter}>
      <option value="">All statuses</option>
      <option value="planned">Planned</option>
      <option value="in_progress">In progress</option>
      <option value="done">Done</option>
    </select>
    <select class="native-input filter-sel" bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each settingsStore.workCategories as cat}
        <option value={cat.id}>{cat.emoji} {cat.name}</option>
      {/each}
    </select>
    <Button onclick={() => { modalWork = "create"; }}>＋ Add work</Button>
  </div>

  <div class="list">
    {#if filteredWorks.length === 0}
      <div class="empty">No works yet — click ＋ Add work to get started.</div>
    {:else}
      {#each filteredWorks as work (work.id)}
        {@const cat = work.categoryId ? categoryMap.get(work.categoryId) : null}
        {@const supplier = work.supplierId ? supplierMap.get(work.supplierId) : null}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <div
          class="card"
          style="border-left-color:{statusColor(work.status)}"
          onclick={() => { modalWork = work; }}
        >
          <div class="card-top">
            <span class="cat-emoji">{cat?.emoji ?? "🔧"}</span>
            <span class="card-title">{work.title}</span>
            <span
              class="status-chip"
              style="background:{statusColor(work.status)}22;color:{statusColor(work.status)};border:1px solid {statusColor(work.status)}44"
            >{statusLabel(work.status)}</span>
          </div>
          <div class="card-meta">
            <span>{work.date}</span>
            {#if supplier}<span>{supplier.name}</span>{/if}
            {#if work.totalCost != null}<span>{fmt(work.totalCost)} €</span>{/if}
            {#if work.placement}<span class="pin-indicator" title="Pinned on floor plan">📍</span>{/if}
          </div>
          {#if work.description}
            <div class="card-desc">{work.description}</div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  <div class="footer">{filteredWorks.length} works · total: {fmt(totalCost)} €</div>
</div>

{#if modalWork !== null}
  <WorkModal
    work={modalWork === "create" ? null : modalWork}
    {store}
    {settingsStore}
    onclose={() => { modalWork = null; }}
    {onplaceonmap}
  />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .toolbar {
    display: flex; gap: var(--space-2); padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border); flex-shrink: 0; align-items: center;
  }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-sel { cursor: pointer; }

  .list { flex: 1; overflow-y: auto; padding: var(--space-3) var(--space-4); display: flex; flex-direction: column; gap: var(--space-2); }
  .empty { color: var(--text-faint); font-size: 13px; text-align: center; padding: 40px 0; }

  .card {
    background: var(--surface); border: 1px solid var(--border); border-left-width: 3px;
    border-radius: var(--radius-md); padding: 10px 14px; cursor: pointer;
  }
  .card:hover { background: var(--surface-hover); }
  .card-top { display: flex; align-items: center; gap: var(--space-2); margin-bottom: 4px; }
  .cat-emoji { font-size: 16px; flex-shrink: 0; }
  .card-title { font-size: 13px; color: var(--text); font-weight: 600; flex: 1; }
  .status-chip { padding: 2px 7px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 500; flex-shrink: 0; }
  .card-meta { display: flex; gap: 12px; font-size: 11px; color: var(--text-faint); flex-wrap: wrap; }
  .pin-indicator { font-size: 11px; }
  .card-desc { font-size: 11px; color: var(--text-faint); margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
