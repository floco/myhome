<script lang="ts">
  import type { createConsumableStore, Consumable } from "../consumableStore.svelte";
  import { stockStatus, barFill } from "../consumableStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import ConsumableModal from "./ConsumableModal.svelte";

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
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Category</th>
          <th>Quantity</th>
          <th>Min</th>
          <th>Stock</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as c (c.id)}
          {@const st = stockStatus(c)}
          {@const fill = barFill(c)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr
            onclick={() => { editConsumable = c; }}
            class:row-low={st === "low"}
            class:row-empty={st === "empty"}
          >
            <td class="emoji-cell">{c.emoji}</td>
            <td class="name-cell">{c.name}</td>
            <td>{categoryName(c.categoryId)}</td>
            <td>{c.quantity} {c.unit}</td>
            <td class="faint">{c.minQuantity} {c.unit}</td>
            <td class="bar-cell">
              <div class="bar-track">
                <div class="bar-fill" style="width:{fill * 100}%;background:{STATUS_COLOR[st]}"></div>
                <div class="bar-min"></div>
              </div>
            </td>
            <td>
              <span class="status-badge" style="color:{STATUS_COLOR[st]};background:{STATUS_COLOR[st]}22">
                {STATUS_LABEL[st]}
              </span>
            </td>
            <td class="actions-cell" onclick={(e) => e.stopPropagation()}>
              {#if onplaceonmap && !c.placement}
                <button class="icon-btn" title="Place on map" onclick={() => onplaceonmap?.(c.id)}>📌</button>
              {/if}
            </td>
          </tr>
        {/each}

        {#if filtered.length === 0}
          <tr>
            <td colspan="8" class="empty">
              {store.consumables.length === 0
                ? "No consumables yet — click ＋ Add consumable to get started."
                : "No consumables match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
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
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th { padding: 6px 10px; color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); cursor: pointer; }
  .emoji-cell { font-size: 16px; width: 32px; text-align: center; }
  .name-cell { color: var(--text); font-weight: 600; }
  .faint { color: var(--text-faint); }
  .actions-cell { white-space: nowrap; text-align: right; }
  .empty { text-align: center; color: var(--text-faint); padding: 32px; }

  .row-low td { background: color-mix(in srgb, #ff9800 6%, transparent); }
  .row-empty td { background: color-mix(in srgb, var(--danger) 8%, transparent); }

  .bar-cell { width: 80px; }
  .bar-track { position: relative; width: 60px; height: 6px; background: var(--surface-alt); border-radius: 3px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 3px; transition: width 0.2s; }
  .bar-min { position: absolute; left: 33.3%; top: 0; bottom: 0; width: 1.5px; background: rgba(255,255,255,0.35); }

  .status-badge { font-size: 10px; padding: 2px 6px; border-radius: 10px; font-weight: 600; letter-spacing: 0.04em; }

  .icon-btn { padding: 4px 8px; border: none; border-radius: var(--radius-sm); background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 13px; }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }

  .footer { padding: 6px 12px; font-size: 11px; color: var(--text-faint); border-top: 1px solid var(--border); flex-shrink: 0; }
</style>
