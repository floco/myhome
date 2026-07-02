<script lang="ts">
  import type { createConsumableStore, Consumable } from "../consumableStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;
  type SettingsStore = Pick<
    ReturnType<typeof createSettingsStore>,
    "consumableUnits" | "consumableCategories"
  >;

  interface Props {
    consumable: Consumable | null;
    store: ConsumableStore;
    settingsStore: SettingsStore;
    onclose: () => void;
    onplaceonmap?: (id: string) => void;
  }

  let { consumable, store, settingsStore, onclose, onplaceonmap }: Props = $props();

  const isCreate = consumable === null;
  const CUSTOM_SENTINEL = "__custom__";
  const DEFAULT_UNITS = ["count", "L", "mL", "kg", "g", "packs", "rolls", "pairs"];

  const availableUnits = $derived(
    settingsStore.consumableUnits?.length ? settingsStore.consumableUnits : DEFAULT_UNITS,
  );

  let activeTab = $state<"details" | "stock">("details");

  let name = $state(consumable?.name ?? "");
  let emoji = $state(consumable?.emoji ?? "🛒");
  let unit = $state(availableUnits.includes(consumable?.unit ?? "count") ? (consumable?.unit ?? "count") : CUSTOM_SENTINEL);
  let customUnit = $state(availableUnits.includes(consumable?.unit ?? "count") ? "" : (consumable?.unit ?? ""));
  let minQuantity = $state(String(consumable?.minQuantity ?? 1));
  let categoryId = $state(consumable?.categoryId ?? "");
  let description = $state(consumable?.description ?? "");

  let newQuantity = $state(String(consumable?.quantity ?? 0));
  let newNote = $state("");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let stockError = $state<string | null>(null);
  let stockSaving = $state(false);

  const currentTransactions = $derived(
    consumable ? store.transactionsFor(consumable.id).slice().reverse() : [],
  );

  const resolvedUnit = $derived(unit === CUSTOM_SENTINEL ? customUnit : unit);

  async function handleSave(): Promise<void> {
    if (!name.trim()) {
      error = "Name is required";
      return;
    }
    saving = true;
    error = null;
    try {
      const payload = {
        name: name.trim(),
        emoji,
        unit: resolvedUnit,
        minQuantity: parseFloat(minQuantity) || 0,
        categoryId: categoryId || null,
        description,
      };
      if (isCreate) {
        await store.createConsumable({ ...payload, quantity: 0 });
      } else {
        await store.updateConsumable(consumable!.id, payload);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!confirmDelete) {
      confirmDelete = true;
      return;
    }
    deleting = true;
    try {
      await store.deleteConsumable(consumable!.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
    } finally {
      deleting = false;
    }
  }

  async function handleUpdateStock(): Promise<void> {
    const qty = parseFloat(newQuantity);
    if (isNaN(qty)) {
      stockError = "Invalid quantity";
      return;
    }
    stockSaving = true;
    stockError = null;
    try {
      await store.updateStock(consumable!.id, qty, newNote);
      newNote = "";
    } catch (e) {
      stockError = e instanceof Error ? e.message : "Update failed";
    } finally {
      stockSaving = false;
    }
  }

  function formatDelta(delta: number): string {
    return delta >= 0 ? `+${delta}` : String(delta);
  }

  function formatTs(iso: string): string {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
</script>

<Modal open={true} title={isCreate ? "Add consumable" : (consumable?.name ?? "")} {onclose}>
  {#snippet children()}
    <div class="tabs">
      <button
        class="tab-btn"
        class:active={activeTab === "details"}
        onclick={() => { activeTab = "details"; }}
      >Details</button>
      {#if !isCreate}
        <button
          class="tab-btn"
          class:active={activeTab === "stock"}
          onclick={() => { activeTab = "stock"; }}
        >Stock</button>
      {/if}
    </div>

    {#if activeTab === "details"}
      <div class="form">
        <div class="row">
          <div class="field short">
            <label>Emoji</label>
            <Input bind:value={emoji} maxlength={4} />
          </div>
          <div class="field grow">
            <label>Name *</label>
            <Input bind:value={name} placeholder="e.g. AA Batteries" />
          </div>
        </div>

        <div class="row">
          <div class="field grow">
            <label>Unit</label>
            <select
              class="native-select"
              bind:value={unit}
            >
              {#each availableUnits as u}
                <option value={u}>{u}</option>
              {/each}
              <option value={CUSTOM_SENTINEL}>Custom…</option>
            </select>
            {#if unit === CUSTOM_SENTINEL}
              <Input bind:value={customUnit} placeholder="e.g. tablets" />
            {/if}
          </div>
          <div class="field short">
            <label>Min qty</label>
            <Input type="number" bind:value={minQuantity} min="0" step="any" />
          </div>
        </div>

        <div class="field">
          <label>Category</label>
          <select class="native-select" bind:value={categoryId}>
            <option value="">— None —</option>
            {#each settingsStore.consumableCategories as cat}
              <option value={cat.id}>{cat.emoji} {cat.name}</option>
            {/each}
          </select>
        </div>

        <div class="field">
          <label>Description</label>
          <textarea bind:value={description} rows="2" class="native-textarea" placeholder="Optional notes…"></textarea>
        </div>

        {#if error}<div class="form-error">{error}</div>{/if}
      </div>

    {:else if activeTab === "stock"}
      <div class="stock-section">
        <div class="current-qty">
          Current stock: <strong>{consumable?.quantity} {consumable?.unit}</strong>
        </div>
        <div class="update-form">
          <div class="row">
            <div class="field grow">
              <label>Set new quantity ({consumable?.unit})</label>
              <Input type="number" bind:value={newQuantity} min="0" step="any" />
            </div>
            <div class="field grow">
              <label>Note (optional)</label>
              <Input bind:value={newNote} placeholder="e.g. restocked" />
            </div>
          </div>
          <Button onclick={handleUpdateStock} disabled={stockSaving}>
            {stockSaving ? "Updating…" : "Update stock"}
          </Button>
          {#if stockError}<div class="form-error">{stockError}</div>{/if}
        </div>

        <div class="history">
          <div class="history-title">History</div>
          {#if currentTransactions.length === 0}
            <div class="history-empty">No transactions yet</div>
          {:else}
            {#each currentTransactions as tx (tx.id)}
              <div class="tx-row">
                <span class="tx-delta" class:positive={tx.delta >= 0} class:negative={tx.delta < 0}>
                  {formatDelta(tx.delta)}
                </span>
                <span class="tx-after">→ {tx.quantityAfter}</span>
                <span class="tx-note">{tx.note || "—"}</span>
                <span class="tx-ts">{formatTs(tx.timestamp)}</span>
                <button class="tx-del" title="Delete" onclick={() => store.deleteTransaction(tx.id)}>✕</button>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    {/if}
  {/snippet}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="delete-confirm">Sure?</span>
        <Button variant="danger" onclick={handleDelete} disabled={deleting}>
          {deleting ? "Deleting…" : "Yes, delete"}
        </Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>Cancel</Button>
      {:else}
        <Button variant="ghost" onclick={() => { confirmDelete = true; }}>Delete</Button>
      {/if}
      {#if onplaceonmap && !consumable?.placement}
        <Button variant="secondary" onclick={() => { onplaceonmap!(consumable!.id); onclose(); }}>📌 Place on map</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="ghost" onclick={onclose}>Cancel</Button>
    {#if activeTab === "details"}
      <Button onclick={handleSave} disabled={saving}>
        {saving ? "Saving…" : isCreate ? "Add" : "Save"}
      </Button>
    {/if}
  {/snippet}
</Modal>

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab-btn {
    padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans);
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { border-bottom-color: var(--accent); color: var(--text); }

  .form { display: flex; flex-direction: column; gap: var(--space-3); }
  .row { display: flex; gap: var(--space-2); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field.grow { flex: 1; }
  .field.short { width: 80px; flex-shrink: 0; }
  label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; }
  .native-select, .native-textarea {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 10px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); width: 100%; box-sizing: border-box;
  }
  .native-select:focus, .native-textarea:focus { outline: none; border-color: var(--accent); }
  .native-textarea { resize: vertical; }
  .form-error { color: var(--danger); font-size: 12px; }

  .stock-section { display: flex; flex-direction: column; gap: var(--space-3); }
  .current-qty { font-size: 13px; color: var(--text-muted); }
  .update-form { display: flex; flex-direction: column; gap: var(--space-2); }

  .history { display: flex; flex-direction: column; gap: 4px; }
  .history-title { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .history-empty { font-size: 12px; color: var(--text-faint); font-style: italic; }
  .tx-row { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 4px 0; border-bottom: 1px solid var(--border); }
  .tx-delta { font-weight: 600; min-width: 40px; }
  .tx-delta.positive { color: var(--success); }
  .tx-delta.negative { color: var(--danger); }
  .tx-after { color: var(--text-muted); min-width: 40px; }
  .tx-note { flex: 1; color: var(--text-muted); }
  .tx-ts { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .tx-del { border: none; background: none; color: var(--text-faint); cursor: pointer; font-size: 10px; padding: 2px 4px; }
  .tx-del:hover { color: var(--danger); }

  .spacer { flex: 1; }
  .delete-confirm { font-size: 12px; color: var(--danger); }
</style>
