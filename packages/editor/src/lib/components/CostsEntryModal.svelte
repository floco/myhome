<script lang="ts">
  import type { createCostsStore, CostEntry } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    entry: CostEntry | null;
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    floorStore: HouseStore;
    onclose: () => void;
  }

  let { entry, costsStore, settingsStore, floorStore, onclose }: Props = $props();

  const isCreate = $derived(entry === null);

  let activeTab = $state<"info" | "media">("info");
  let categoryId = $state("");
  let date = $state("");
  let totalAmount = $state("");
  let quantity = $state("");
  let unitPrice = $state("");
  let supplierId = $state("");
  let notes = $state("");
  let roomId = $state("");

  $effect(() => {
    categoryId = entry?.categoryId ?? settingsStore.costCategories[0]?.id ?? "";
    date = entry?.date ?? new Date().toISOString().slice(0, 10);
    totalAmount = entry?.totalAmount != null ? String(entry.totalAmount) : "";
    quantity = entry?.quantity != null ? String(entry.quantity) : "";
    unitPrice = entry?.unitPrice != null ? String(entry.unitPrice) : "";
    supplierId = entry?.supplierId ?? "";
    notes = entry?.notes ?? "";
    roomId = entry?.roomId ?? "";
    activeTab = "info";
    confirmDelete = false;
    error = null;
  });

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const selectedCategory = $derived(
    settingsStore.costCategories.find(c => c.id === categoryId) ?? null
  );
  const hasUnit = $derived(selectedCategory?.unit != null);
  const allRooms = $derived(
    floorStore.floors.flatMap((f: { rooms: { id: string; label: string }[] }) => f.rooms)
  );

  const currentEntry = $derived(
    entry ? (costsStore.entries.find(e => e.id === entry!.id) ?? entry) : null
  );
  const attachmentCount = $derived(currentEntry?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentEntry?.attachments ?? []).map(fname => {
      const url = `/api/costs/entries/${entry!.id}/attachments/${fname}`;
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

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

  async function handleSave(): Promise<void> {
    if (!categoryId) { error = "Category is required"; return; }
    if (!date) { error = "Date is required"; return; }
    const parsedTotal = parseFloat(totalAmount);
    if (isNaN(parsedTotal) || parsedTotal <= 0) { error = "Total amount is required"; return; }
    saving = true; error = null;
    const patch = {
      categoryId, date, totalAmount: parsedTotal,
      quantity: quantity ? parseFloat(quantity) || null : null,
      unitPrice: unitPrice ? parseFloat(unitPrice) || null : null,
      supplierId: supplierId || null,
      notes: notes.trim(),
      roomId: roomId || null,
    };
    try {
      if (isCreate) { await costsStore.createEntry(patch); } else { await costsStore.updateEntry(entry!.id, patch); }
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
    try { await costsStore.deleteEntry(entry.id); onclose(); }
    catch (e) { error = e instanceof Error ? e.message : "Delete failed"; deleting = false; }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!entry) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await costsStore.uploadAttachment(entry.id, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Upload failed"; }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!entry) return;
    try { await costsStore.deleteAttachment(entry.id, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Delete failed"; }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }
</script>

<Modal open={true} title={isCreate ? "＋ New entry" : "Edit entry"} {onclose} width="520px">
  <Tabs
    tabs={[
      { id: "info", label: "Info" },
      { id: "media", label: attachmentCount > 0 ? `Media (${attachmentCount})` : "Media", disabled: isCreate },
    ]}
    active={activeTab}
    onchange={(id) => { activeTab = id as "info" | "media"; }}
  />

  {#if activeTab === "info"}
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
        <input class="native-input num-input" bind:value={quantity} type="number" min="0" step="any" placeholder="0" oninput={() => autoCalc("qty")} />
        <label style="margin-left:12px">Unit price (€/{selectedCategory!.unit})</label>
        <input class="native-input num-input" bind:value={unitPrice} type="number" min="0" step="any" placeholder="0.00" oninput={() => autoCalc("price")} />
      </div>
    {/if}

    <div class="row">
      <label>Total amount (€) *</label>
      <input class="native-input num-input" bind:value={totalAmount} type="number" min="0" step="any" placeholder="0.00" oninput={() => autoCalc("total")} />
    </div>

    <div class="row">
      <label>Supplier</label>
      <select class="native-input flex-grow" bind:value={supplierId}>
        <option value="">— No supplier —</option>
        {#each settingsStore.suppliers as s}<option value={s.id}>{s.name}</option>{/each}
      </select>
    </div>

    <div class="row">
      <label>Room</label>
      <select class="native-input flex-grow" bind:value={roomId}>
        <option value="">No room</option>
        {#each allRooms as room}<option value={room.id}>{room.label}</option>{/each}
      </select>
    </div>

    <div class="row col">
      <label>Notes</label>
      <textarea class="native-input" bind:value={notes} rows="2" placeholder="Optional notes…"></textarea>
    </div>

    {#if error}<div class="error">{error}</div>{/if}
  {:else}
    <MediaGallery
      items={mediaItems}
      {uploading}
      {uploadError}
      onUpload={handleUpload}
      onDelete={handleDeleteAttachment}
      onItemClick={handleItemClick}
    />
  {/if}

  {#snippet footer()}
    <span class="spacer"></span>
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete this entry?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>{deleting ? "…" : "Confirm delete"}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>Cancel</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
    {/if}
    {#if activeTab === "info"}
      <Button variant="primary" disabled={saving} onclick={handleSave}>
        {saving ? "Saving…" : isCreate ? "Create" : "Save"}
      </Button>
    {/if}
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

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
