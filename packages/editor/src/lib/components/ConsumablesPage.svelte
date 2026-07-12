<script lang="ts">
  import type { createConsumableStore, Consumable } from "../consumableStore.svelte";
  import { stockStatus, barFill } from "../consumableStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import ConsumableModal from "./ConsumableModal.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;
  type SettingsStore = Pick<ReturnType<typeof createSettingsStore>, "consumableCategories" | "consumableUnits">;

  interface Props {
    store: ConsumableStore;
    settingsStore: SettingsStore;
    onplaceonmap?: (id: string) => void;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }

  let { store, settingsStore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();

  let searchQuery = $state("");
  let categoryFilter = $state("");
  let attentionFilter = $state(false);
  let editConsumable = $state<Consumable | null>(null);
  let showCreate = $state(false);

  $effect(() => {
    if (selectedItemId) {
      const found = store.consumables.find((c) => c.id === selectedItemId);
      if (found) {
        editConsumable = found;
        onclearselection?.();
      }
    }
  });

  const STATUS_COLOR: Record<string, string> = {
    ok: "var(--success)",
    low: "#ff9800",
    empty: "var(--danger)",
  };
  const STATUS_LABEL: Record<string, string> = { ok: "OK", low: "LOW", empty: "EMPTY" };

  const filtered = $derived(
    store.consumables.filter((c) => {
      if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase()))
        return false;
      if (categoryFilter && c.categoryId !== categoryFilter) return false;
      if (attentionFilter) {
        const s = stockStatus(c);
        if (s === "ok") return false;
      }
      return true;
    }),
  );

  function categoryName(id: string | null): string {
    if (!id) return "—";
    return settingsStore.consumableCategories.find((c) => c.id === id)?.name ?? "—";
  }
</script>

<div class="page">
  <div class="toolbar">
    <Input placeholder="🔍 Search…" bind:value={searchQuery} />
    <select class="native-select" bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each settingsStore.consumableCategories as cat}
        <option value={cat.id}>{cat.emoji} {cat.name}</option>
      {/each}
    </select>
    <div class="filter-toggle">
      <button
        class="toggle-btn"
        class:active={!attentionFilter}
        onclick={() => { attentionFilter = false; }}
        title="All"
      >☰</button>
      <button
        class="toggle-btn"
        class:active={attentionFilter}
        onclick={() => { attentionFilter = true; }}
        title="Needs attention"
      >⚠</button>
    </div>
    <Button onclick={() => { showCreate = true; }}>＋ Add consumable</Button>
  </div>

  <div class="table-wrapper">
    {#snippet emojiCell(c: Consumable)}
      {c.emoji}
    {/snippet}
    {#snippet nameCell(c: Consumable)}
      {c.name}
    {/snippet}
    {#snippet categoryCell(c: Consumable)}
      {categoryName(c.categoryId)}
    {/snippet}
    {#snippet quantityCell(c: Consumable)}
      {c.quantity} {c.unit}
    {/snippet}
    {#snippet minCell(c: Consumable)}
      {c.minQuantity} {c.unit}
    {/snippet}
    {#snippet stockCell(c: Consumable)}
      {@const st = stockStatus(c)}
      {@const fill = barFill(c)}
      <div class="bar-track">
        <div class="bar-fill" style="width:{fill * 100}%;background:{STATUS_COLOR[st]}"></div>
        <div class="bar-min"></div>
      </div>
    {/snippet}
    {#snippet statusCell(c: Consumable)}
      {@const st = stockStatus(c)}
      <span class="status-badge" style="color:{STATUS_COLOR[st]};background:{STATUS_COLOR[st]}22">
        {STATUS_LABEL[st]}
      </span>
    {/snippet}
    {#snippet actionsCell(c: Consumable)}
      {#if onplaceonmap && !c.placement}
        <button class="icon-btn" title="Place on map" onclick={() => onplaceonmap?.(c.id)}>📌</button>
      {/if}
    {/snippet}

    <SortableTable
      columns={[
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "name", label: "Name", sortValue: (c) => c.name, cellClass: "name-cell", cell: nameCell },
        { key: "category", label: "Category", sortValue: (c) => categoryName(c.categoryId), cell: categoryCell },
        { key: "quantity", label: "Quantity", sortValue: (c) => c.quantity, cell: quantityCell },
        { key: "min", label: "Min", cellClass: "faint", sortValue: (c) => c.minQuantity, cell: minCell },
        { key: "stock", label: "Stock", sortable: false, cellClass: "bar-cell", cell: stockCell },
        { key: "status", label: "Status", sortValue: (c) => stockStatus(c), cell: statusCell },
        { key: "actions", label: "", sortable: false, cellClass: "actions-cell", stopRowClick: true, cell: actionsCell },
      ] as Column<Consumable>[]}
      rows={filtered}
      rowKey={(c) => c.id}
      rowClick={(c) => { editConsumable = c; }}
      rowClass={(c) => {
        const st = stockStatus(c);
        return st === "low" ? "row-low" : st === "empty" ? "row-empty" : "";
      }}
      emptyMessage={store.consumables.length === 0
        ? "No consumables yet — click ＋ Add consumable to get started."
        : "No consumables match your filters."}
    />
  </div>

  <div class="footer">{filtered.length} item{filtered.length !== 1 ? "s" : ""}</div>
</div>

{#if showCreate || editConsumable}
  <ConsumableModal
    consumable={editConsumable ?? null}
    {store}
    {settingsStore}
    onclose={() => { showCreate = false; editConsumable = null; }}
    {onplaceonmap}
  />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; flex-wrap: wrap;
  }
  .toolbar :global(.ui-input) { flex: 1; min-width: 140px; }
  .native-select {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-select:focus { outline: none; border-color: var(--accent); }
  .filter-toggle { display: flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; flex-shrink: 0; }
  .toggle-btn { padding: 6px 10px; border: none; background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 11px; white-space: nowrap; }
  .toggle-btn:not(:last-child) { border-right: 1px solid var(--border); }
  .toggle-btn.active { background: var(--accent); color: var(--accent-contrast); }
  .toggle-btn:not(.active):hover { background: var(--surface-hover); color: var(--text); }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  :global(.faint) { color: var(--text-faint); }
  :global(.actions-cell) { white-space: nowrap; text-align: right; }

  :global(.row-low td) { background: color-mix(in srgb, #ff9800 6%, transparent); }
  :global(.row-empty td) { background: color-mix(in srgb, var(--danger) 8%, transparent); }

  :global(.bar-cell) { width: 80px; }
  .bar-track { position: relative; width: 60px; height: 6px; background: var(--surface-alt); border-radius: 3px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 3px; transition: width 0.2s; }
  .bar-min { position: absolute; left: 33.3%; top: 0; bottom: 0; width: 1.5px; background: rgba(255,255,255,0.35); }

  .status-badge { font-size: 10px; padding: 2px 6px; border-radius: 10px; font-weight: 600; letter-spacing: 0.04em; }

  .icon-btn { padding: 4px 8px; border: none; border-radius: var(--radius-sm); background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 13px; }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }

  .footer { padding: 6px 12px; font-size: 11px; color: var(--text-faint); border-top: 1px solid var(--border); flex-shrink: 0; }
</style>
