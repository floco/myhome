<!-- packages/editor/src/lib/components/CostsEntryModal.svelte -->
<script lang="ts">
  import type { createCostsStore, CostEntry } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import DatePicker from "./DatePicker.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    entry: CostEntry | null; // null = create mode
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    floorStore: HouseStore;
    onclose: () => void;
  }

  let { entry, costsStore, settingsStore, floorStore, onclose }: Props = $props();

  const isCreate = entry === null;

  let categoryId = $state(entry?.categoryId ?? settingsStore.costCategories[0]?.id ?? "");
  let date = $state(entry?.date ?? new Date().toISOString().slice(0, 10));
  let totalAmount = $state<string>(entry?.totalAmount != null ? String(entry.totalAmount) : "");
  let quantity = $state<string>(entry?.quantity != null ? String(entry.quantity) : "");
  let unitPrice = $state<string>(entry?.unitPrice != null ? String(entry.unitPrice) : "");
  let supplier = $state(entry?.supplier ?? "");
  let notes = $state(entry?.notes ?? "");
  let roomId = $state(entry?.roomId ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);

  const selectedCategory = $derived(
    settingsStore.costCategories.find(c => c.id === categoryId) ?? null
  );
  const hasUnit = $derived(selectedCategory?.unit != null);

  // Auto-calculate the third value when two are known
  function autoCalc(changed: "total" | "qty" | "price"): void {
    const tot = parseFloat(totalAmount);
    const qty = parseFloat(quantity);
    const ppu = parseFloat(unitPrice);
    const totOk = !isNaN(tot) && tot > 0;
    const qtyOk = !isNaN(qty) && qty > 0;
    const ppuOk = !isNaN(ppu) && ppu > 0;

    if ((changed === "qty" || changed === "price") && qtyOk && ppuOk) {
      // qty × price → always update total
      totalAmount = (qty * ppu).toFixed(2);
    } else if (changed === "total" && totOk && qtyOk) {
      // total / qty → update unit price
      unitPrice = (tot / qty).toFixed(4);
    } else if (changed === "total" && totOk && ppuOk && quantity === "") {
      // total / price → update qty (only when qty is empty)
      quantity = (tot / ppu).toFixed(2);
    }
  }

  const allRooms = $derived(
    floorStore.floors.flatMap((f: { rooms: { id: string; label: string }[] }) => f.rooms)
  );

  async function handleSave(): Promise<void> {
    if (!categoryId) { error = "Category is required"; return; }
    if (!date) { error = "Date is required"; return; }
    const parsedTotal = parseFloat(totalAmount);
    if (isNaN(parsedTotal) || parsedTotal <= 0) { error = "Total amount is required"; return; }

    saving = true; error = null;
    const patch = {
      categoryId,
      date,
      totalAmount: parsedTotal,
      quantity: quantity ? parseFloat(quantity) || null : null,
      unitPrice: unitPrice ? parseFloat(unitPrice) || null : null,
      supplier: supplier.trim() || null,
      notes: notes.trim(),
      roomId: roomId || null,
    };
    try {
      if (isCreate) {
        await costsStore.createEntry(patch);
      } else {
        await costsStore.updateEntry(entry!.id, patch);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!entry) return;
    deleting = true;
    try {
      await costsStore.deleteEntry(entry.id);
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
      <h2>{isCreate ? "＋ New entry" : "Edit entry"}</h2>
      <button class="close-btn" onclick={onclose}>✕</button>
    </div>

    <div class="modal-body">
      <div class="row">
        <label>Category *</label>
        <select class="flex-input" bind:value={categoryId}>
          {#each settingsStore.costCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>

      <div class="row">
        <label>Date *</label>
        <DatePicker bind:value={date} />
      </div>

      {#if hasUnit}
        <div class="row">
          <label>Quantity ({selectedCategory!.unit})</label>
          <input
            class="num-input"
            bind:value={quantity}
            type="number"
            min="0"
            step="any"
            placeholder="0"
            oninput={() => autoCalc("qty")}
          />
          <label style="margin-left:12px">Unit price (€/{selectedCategory!.unit})</label>
          <input
            class="num-input"
            bind:value={unitPrice}
            type="number"
            min="0"
            step="any"
            placeholder="0.00"
            oninput={() => autoCalc("price")}
          />
        </div>
      {/if}

      <div class="row">
        <label>Total amount (€) *</label>
        <input
          class="num-input"
          bind:value={totalAmount}
          type="number"
          min="0"
          step="any"
          placeholder="0.00"
          oninput={() => autoCalc("total")}
        />
      </div>

      <div class="row">
        <label>Supplier</label>
        <input class="flex-input" bind:value={supplier} placeholder="Optional" />
      </div>

      <div class="row">
        <label>Room</label>
        <select class="flex-input" bind:value={roomId}>
          <option value="">No room</option>
          {#each allRooms as room}
            <option value={room.id}>{room.label}</option>
          {/each}
        </select>
      </div>

      <div class="row col">
        <label>Notes</label>
        <textarea bind:value={notes} rows="2" placeholder="Optional notes…"></textarea>
      </div>

      {#if error}<div class="error">{error}</div>{/if}
    </div>

    <div class="modal-footer">
      <span class="spacer"></span>
      {#if !isCreate}
        {#if confirmDelete}
          <span class="confirm-text">Delete this entry?</span>
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
    background: rgba(0,0,0,.6);
    display: flex; align-items: center; justify-content: center;
  }
  .modal {
    background: #1a1a30; border: 1px solid #3a3a5a; border-radius: 10px;
    width: 520px; max-width: 95vw; max-height: 90vh;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 8px 32px #0008;
  }
  .modal-header {
    display: flex; align-items: center; padding: 14px 18px;
    border-bottom: 1px solid #2a2a4a; flex-shrink: 0;
  }
  h2 { margin: 0; font-size: 15px; color: #eee; font-family: sans-serif; font-weight: 600; flex: 1; }
  .close-btn { background: none; border: none; color: #667; font-size: 16px; cursor: pointer; }
  .close-btn:hover { color: #aaa; }

  .modal-body { padding: 16px 18px; overflow-y: auto; flex: 1; font-family: sans-serif; }
  .row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
  .row.col { flex-direction: column; align-items: stretch; }
  label { font-size: 11px; color: #778; white-space: nowrap; }
  input, select, textarea {
    background: #0f0f24; border: 1px solid #2a2a4a; color: #ccc;
    padding: 5px 8px; border-radius: 4px;
    font-size: 12px; font-family: sans-serif;
  }
  input:focus, select:focus, textarea:focus { outline: none; border-color: #5566cc; }
  .flex-input { flex: 1; min-width: 0; }
  .num-input { width: 110px; }
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
  .save-btn:disabled { opacity: .5; cursor: default; }
  .delete-btn { background: none; border: 1px solid #3a1a1a; color: #c66; }
  .delete-btn:hover { background: #2a1010; }
  .danger-btn { background: #3a1010; border: none; color: #f88; }
  .danger-btn:hover:not(:disabled) { background: #4a1515; }
  .danger-btn:disabled { opacity: .5; cursor: default; }
  .confirm-text { font-size: 11px; color: #c66; }
  button:not(.save-btn):not(.danger-btn):not(.delete-btn):not(.close-btn) {
    background: none; border: 1px solid #2a2a4a; color: #778;
  }
</style>
