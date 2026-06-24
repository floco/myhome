<script lang="ts">
  import type { createCostsStore, CostEntry } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";

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
  let supplierId = $state(entry?.supplierId ?? "");
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
      totalAmount = (qty * ppu).toFixed(2);
    } else if (changed === "total" && totOk && qtyOk) {
      unitPrice = (tot / qty).toFixed(4);
    } else if (changed === "total" && totOk && ppuOk && quantity === "") {
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
      supplierId: supplierId || null,
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

<Modal open={true} title={isCreate ? "＋ New entry" : "Edit entry"} {onclose} width="520px">
  <div class="row">
    <label>Category *</label>
    <select class="native-input flex-grow" bind:value={categoryId}>
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
        class="native-input num-input"
        bind:value={quantity}
        type="number"
        min="0"
        step="any"
        placeholder="0"
        oninput={() => autoCalc("qty")}
      />
      <label style="margin-left:12px">Unit price (€/{selectedCategory!.unit})</label>
      <input
        class="native-input num-input"
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
      class="native-input num-input"
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
    <select class="native-input flex-grow" bind:value={supplierId}>
      <option value="">— No supplier —</option>
      {#each settingsStore.suppliers as s}
        <option value={s.id}>{s.name}</option>
      {/each}
    </select>
  </div>

  <div class="row">
    <label>Room</label>
    <select class="native-input flex-grow" bind:value={roomId}>
      <option value="">No room</option>
      {#each allRooms as room}
        <option value={room.id}>{room.label}</option>
      {/each}
    </select>
  </div>

  <div class="row col">
    <label>Notes</label>
    <textarea class="native-input" bind:value={notes} rows="2" placeholder="Optional notes…"></textarea>
  </div>

  {#if error}<div class="error">{error}</div>{/if}

  {#snippet footer()}
    <span class="spacer"></span>
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete this entry?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>
          {deleting ? "…" : "Confirm delete"}
        </Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>Cancel</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
    {/if}
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? "Saving…" : isCreate ? "Create" : "Save"}
    </Button>
  {/snippet}
</Modal>

<style>
  .row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
  .row.col { flex-direction: column; align-items: stretch; }
  .flex-grow { flex: 1; min-width: 0; }
  label { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md);
    font-size: 13px; font-family: var(--font-sans); box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .native-input::placeholder { color: var(--text-faint); }
  select.native-input { cursor: pointer; }
  .num-input { width: 120px; }
  textarea.native-input { width: 100%; resize: vertical; }
  .error { color: var(--danger); font-size: 11px; margin-top: 4px; font-family: var(--font-sans); }

  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
