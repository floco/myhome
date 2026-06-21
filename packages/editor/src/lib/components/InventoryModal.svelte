<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import DatePicker from "./DatePicker.svelte";

  type InvStore = ReturnType<typeof createInventoryStore>;

  interface Props {
    item: InventoryItem | null; // null = create mode
    store: InvStore;
    inventoryCategories: string[];
    onclose: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let { item, store, inventoryCategories, onclose, onplaceonmap }: Props = $props();

  const isCreate = item === null;

  let name = $state(item?.name ?? "");
  let emoji = $state(item?.emoji ?? "📦");
  let category = $state(item?.category ?? "");
  let brand = $state(item?.brand ?? "");
  let model = $state(item?.model ?? "");
  let serialNumber = $state(item?.serialNumber ?? "");
  let purchaseDate = $state(item?.purchaseDate ?? "");
  let purchasePrice = $state<string>(
    item?.purchasePrice != null ? String(item.purchasePrice) : ""
  );
  let warrantyExpiryDate = $state(item?.warrantyExpiryDate ?? "");
  let notes = $state(item?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true; error = null;
    const parsedPrice = purchasePrice ? parseFloat(purchasePrice) : null;
    const patch = {
      name: name.trim(),
      emoji: emoji || "📦",
      category: category.trim(),
      brand: brand.trim() || null,
      model: model.trim() || null,
      serialNumber: serialNumber.trim() || null,
      purchaseDate: purchaseDate || null,
      purchasePrice: parsedPrice !== null && !isNaN(parsedPrice) ? parsedPrice : null,
      warrantyExpiryDate: warrantyExpiryDate || null,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createItem(patch);
      } else {
        await store.updateItem(item!.id, patch);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!item) return;
    deleting = true;
    try {
      await store.deleteItem(item.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
      deleting = false;
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="overlay" onclick={(e) => { if (e.target === e.currentTarget) onclose(); }}>
  <div class="modal">
    <div class="modal-header">
      <h2>{isCreate ? "＋ New item" : "Edit item"}</h2>
      <button class="close-btn" onclick={onclose}>✕</button>
    </div>

    <div class="modal-body">
      <div class="row">
        <label>Emoji</label>
        <input class="emoji-input" bind:value={emoji} maxlength="2" />
        <label style="margin-left:16px">Name *</label>
        <input class="flex-input" bind:value={name} placeholder='e.g. Samsung TV 65"' />
      </div>
      <div class="row">
        <label>Category</label>
        <input
          class="flex-input"
          bind:value={category}
          list="inv-cat-list"
          placeholder="Electronics, Furniture…"
        />
        <datalist id="inv-cat-list">
          {#each inventoryCategories as s}<option value={s} />{/each}
        </datalist>
      </div>
      <div class="row">
        <label>Brand</label>
        <input class="flex-input" bind:value={brand} placeholder="Samsung" />
        <label style="margin-left:12px">Model</label>
        <input class="flex-input" bind:value={model} placeholder="QE65Q80C" />
      </div>
      <div class="row">
        <label>Serial #</label>
        <input class="flex-input" bind:value={serialNumber} placeholder="XYZ123" />
      </div>
      <div class="row">
        <label>Purchased</label>
        <DatePicker bind:value={purchaseDate} />
        <label style="margin-left:12px">Price (€)</label>
        <input
          class="price-input"
          bind:value={purchasePrice}
          type="number"
          min="0"
          step="0.01"
          placeholder="0.00"
        />
      </div>
      <div class="row">
        <label>Warranty expiry</label>
        <DatePicker bind:value={warrantyExpiryDate} />
      </div>
      <div class="row col">
        <label>Notes</label>
        <textarea bind:value={notes} rows="3" placeholder="Additional notes…"></textarea>
      </div>
      {#if error}<div class="error">{error}</div>{/if}
    </div>

    <div class="modal-footer">
      {#if !isCreate && onplaceonmap}
        <button class="place-btn" onclick={() => onplaceonmap!(item!.id)}>
          📍 Place on map
        </button>
      {/if}
      <span class="spacer"></span>
      {#if !isCreate}
        {#if confirmDelete}
          <span class="confirm-text">Delete this item?</span>
          <button class="danger-btn" disabled={deleting} onclick={handleDelete}>
            {deleting ? "…" : "Confirm delete"}
          </button>
          <button onclick={() => { confirmDelete = false; }}>Cancel</button>
        {:else}
          <button class="delete-btn" onclick={() => { confirmDelete = true; }}>🗑 Delete</button>
        {/if}
      {/if}
      <button class="save-btn" disabled={saving} onclick={handleSave}>
        {saving ? "Saving…" : isCreate ? "Create" : "Save"}
      </button>
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed; inset: 0; z-index: 200;
    background: rgba(0, 0, 0, 0.6);
    display: flex; align-items: center; justify-content: center;
  }
  .modal {
    background: #1a1a30; border: 1px solid #3a3a5a; border-radius: 10px;
    width: 560px; max-width: 95vw; max-height: 90vh;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 8px 32px #0008;
  }
  .modal-header {
    display: flex; align-items: center; padding: 14px 18px;
    border-bottom: 1px solid #2a2a4a; flex-shrink: 0;
  }
  h2 {
    margin: 0; font-size: 15px; color: #eee;
    font-family: sans-serif; font-weight: 600; flex: 1;
  }
  .close-btn {
    background: none; border: none; color: #667; font-size: 16px; cursor: pointer;
  }
  .close-btn:hover { color: #aaa; }

  .modal-body {
    padding: 16px 18px; overflow-y: auto; flex: 1; font-family: sans-serif;
  }
  .row {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 12px; flex-wrap: wrap;
  }
  .row.col { flex-direction: column; align-items: stretch; }
  label { font-size: 11px; color: #778; white-space: nowrap; }
  input, textarea {
    background: #0f0f24; border: 1px solid #2a2a4a; color: #ccc;
    padding: 5px 8px; border-radius: 4px;
    font-size: 12px; font-family: sans-serif;
  }
  input:focus, textarea:focus { outline: none; border-color: #5566cc; }
  .flex-input { flex: 1; min-width: 0; }
  .emoji-input { width: 42px; text-align: center; font-size: 18px; }
  .price-input { width: 90px; }
  textarea { resize: vertical; }
  .error { color: #f44336; font-size: 11px; margin-top: 4px; font-family: sans-serif; }

  .modal-footer {
    display: flex; align-items: center; gap: 8px; padding: 12px 18px;
    border-top: 1px solid #2a2a4a; flex-shrink: 0; flex-wrap: wrap;
    font-family: sans-serif;
  }
  .spacer { flex: 1; }
  button { padding: 5px 14px; border-radius: 4px; font-size: 12px; cursor: pointer; }
  .save-btn { background: #1a3a2a; border: none; color: #4c9; }
  .save-btn:hover:not(:disabled) { background: #224a34; }
  .save-btn:disabled { opacity: 0.5; cursor: default; }
  .delete-btn { background: none; border: 1px solid #3a1a1a; color: #c66; }
  .delete-btn:hover { background: #2a1010; }
  .danger-btn { background: #3a1010; border: none; color: #f88; }
  .danger-btn:hover:not(:disabled) { background: #4a1515; }
  .danger-btn:disabled { opacity: 0.5; cursor: default; }
  .place-btn { background: #1a2a3a; border: 1px solid #2a4a5a; color: #78c; }
  .place-btn:hover { background: #1f3548; }
  .confirm-text { font-size: 11px; color: #c66; }
  button:not(.save-btn):not(.danger-btn):not(.delete-btn):not(.place-btn):not(.close-btn) {
    background: none; border: 1px solid #2a2a4a; color: #778;
  }
</style>
