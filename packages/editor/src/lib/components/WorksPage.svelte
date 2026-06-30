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

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Title</th>
          <th>Category</th>
          <th>Date</th>
          <th>Supplier</th>
          <th>Cost</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {#each filteredWorks as work (work.id)}
          {@const cat = work.categoryId ? categoryMap.get(work.categoryId) : null}
          {@const supplier = work.supplierId ? supplierMap.get(work.supplierId) : null}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { modalWork = work; }}>
            <td class="emoji-cell">{cat?.emoji ?? "🔧"}</td>
            <td class="name-cell">
              {work.title}
              {#if work.description}<span class="desc">{work.description}</span>{/if}
            </td>
            <td>{cat?.name ?? "—"}</td>
            <td>{work.date}</td>
            <td>{supplier?.name ?? "—"}</td>
            <td>{work.totalCost != null ? fmt(work.totalCost) + " €" : "—"}</td>
            <td>
              <span
                class="status-chip"
                style="background:{statusColor(work.status)}22;color:{statusColor(work.status)};border:1px solid {statusColor(work.status)}44"
              >{statusLabel(work.status)}</span>
              {#if work.placement}<span class="pin-indicator" title="Pinned">📍</span>{/if}
            </td>
          </tr>
        {/each}
        {#if filteredWorks.length === 0}
          <tr>
            <td colspan="7" class="empty">
              {store.works.length === 0 ? "No works yet — click ＋ Add work to get started." : "No works match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
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
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-sel { cursor: pointer; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); cursor: pointer; }
  .emoji-cell { font-size: 16px; width: 32px; text-align: center; }
  .name-cell { color: var(--text); font-weight: 600; }
  .desc { font-size: 11px; color: var(--text-faint); font-weight: 400; margin-left: 6px; }
  .status-chip { padding: 2px 7px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 500; }
  .pin-indicator { font-size: 11px; margin-left: 4px; }
  .empty { text-align: center; color: var(--text-faint); padding: 32px; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
