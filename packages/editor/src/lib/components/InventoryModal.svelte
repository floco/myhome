<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type InvStore = ReturnType<typeof createInventoryStore>;

  interface Props {
    item: InventoryItem | null;
    store: InvStore;
    inventoryCategories: string[];
    onclose: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let { item, store, inventoryCategories, onclose, onplaceonmap }: Props = $props();

  const isCreate = item === null;

  let activeTab = $state<"info" | "media">("info");
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
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const currentItem = $derived(
    item ? (store.items.find((i) => i.id === item.id) ?? item) : null
  );
  const attachmentCount = $derived(currentItem?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentItem?.attachments ?? []).map(fname => {
      const url = apiUrl(`/api/inventory/items/${item!.id}/attachments/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

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

  async function handleUpload(files: File[]): Promise<void> {
    if (!item) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) await store.uploadAttachment(item.id, file);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Upload failed";
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!item) return;
    try {
      await store.deleteAttachment(item.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Delete failed";
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }
</script>

<Modal open={true} title={isCreate ? "＋ New item" : "Edit item"} {onclose} width="560px">
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
      <label>Emoji</label>
      <EmojiPicker bind:value={emoji} />
      <label style="margin-left:16px">Name *</label>
      <div class="flex-grow"><Input bind:value={name} placeholder='e.g. Samsung TV 65"' /></div>
    </div>
    <div class="row">
      <label>Category</label>
      <input
        class="native-input flex-grow"
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
      <div class="flex-grow"><Input bind:value={brand} placeholder="Samsung" /></div>
      <label style="margin-left:12px">Model</label>
      <div class="flex-grow"><Input bind:value={model} placeholder="QE65Q80C" /></div>
    </div>
    <div class="row">
      <label>Serial #</label>
      <div class="flex-grow"><Input bind:value={serialNumber} placeholder="XYZ123" /></div>
    </div>
    <div class="row">
      <label>Purchased</label>
      <DatePicker bind:value={purchaseDate} />
      <label style="margin-left:12px">Price (€)</label>
      <input
        class="native-input price-input"
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
      <textarea class="native-input" bind:value={notes} rows="3" placeholder="Additional notes…"></textarea>
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
    {#if !isCreate && onplaceonmap}
      <Button variant="secondary" onclick={() => onplaceonmap!(item!.id)}>📍 Place on map</Button>
    {/if}
    <span class="spacer"></span>
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete this item?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>
          {deleting ? "…" : "Confirm delete"}
        </Button>
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
  .row {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 12px; flex-wrap: wrap;
  }
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
  .emoji-input { width: 56px; text-align: center; font-size: 18px; }
  .price-input { width: 100px; }
  textarea.native-input { width: 100%; resize: vertical; }
  .error { color: var(--danger); font-size: 11px; margin-top: 4px; font-family: var(--font-sans); }

  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
