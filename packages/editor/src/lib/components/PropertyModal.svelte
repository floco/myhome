<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createPropertiesStore, Property, PropertyType, PropertyStatus } from "../propertiesStore.svelte";
  import type { createLocationsStore } from "../locationsStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type PropertiesStore = ReturnType<typeof createPropertiesStore>;
  type LocationsStore = ReturnType<typeof createLocationsStore>;

  interface Props {
    property: Property | null;
    store: PropertiesStore;
    locationsStore: LocationsStore;
    onclose: () => void;
  }

  let { property, store, locationsStore, onclose }: Props = $props();

  const isCreate = property === null;

  let activeTab = $state<"info" | "pros_cons" | "notes" | "media">("info");
  let name = $state(property?.name ?? "");
  let emoji = $state(property?.emoji ?? "🏠");
  let type = $state<PropertyType>(property?.type ?? "house");
  let status = $state<PropertyStatus>(property?.status ?? "watching");
  let locationId = $state(property?.locationId ?? "");
  let address = $state(property?.address ?? "");
  let price = $state<string>(property?.price != null ? String(property.price) : "");
  let landSize = $state<string>(property?.landSize != null ? String(property.landSize) : "");
  let builtSize = $state<string>(property?.builtSize != null ? String(property.builtSize) : "");
  let bedrooms = $state<string>(property?.bedrooms != null ? String(property.bedrooms) : "");
  let bathrooms = $state<string>(property?.bathrooms != null ? String(property.bathrooms) : "");
  let listingUrl = $state(property?.listingUrl ?? "");
  let contact = $state(property?.contact ?? "");
  let pros = $state<string[]>(property?.pros ? [...property.pros] : []);
  let cons = $state<string[]>(property?.cons ? [...property.cons] : []);
  let newPro = $state("");
  let newCon = $state("");
  let notes = $state(property?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  function addPro(): void {
    const v = newPro.trim();
    if (!v) return;
    pros = [...pros, v];
    newPro = "";
  }
  function removePro(index: number): void {
    pros = pros.filter((_, i) => i !== index);
  }
  function addCon(): void {
    const v = newCon.trim();
    if (!v) return;
    cons = [...cons, v];
    newCon = "";
  }
  function removeCon(index: number): void {
    cons = cons.filter((_, i) => i !== index);
  }

  function parseNum(v: string): number | null {
    if (!v) return null;
    const n = parseFloat(v);
    return isNaN(n) ? null : n;
  }
  function parseIntOrNull(v: string): number | null {
    if (!v) return null;
    const n = parseInt(v, 10);
    return isNaN(n) ? null : n;
  }

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = $_('inventory.modal.nameRequired'); return; }
    saving = true; error = null;
    const patch = {
      name: name.trim(),
      emoji: emoji || "🏠",
      type,
      status,
      locationId: locationId || null,
      address: address.trim(),
      price: parseNum(price),
      landSize: parseNum(landSize),
      builtSize: parseNum(builtSize),
      bedrooms: parseIntOrNull(bedrooms),
      bathrooms: parseIntOrNull(bathrooms),
      listingUrl: listingUrl.trim() || null,
      contact: contact.trim(),
      pros,
      cons,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createProperty(patch);
      } else {
        await store.updateProperty(property!.id, patch);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('inventory.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!property) return;
    deleting = true;
    try {
      await store.deleteProperty(property.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('inventory.modal.deleteFailed');
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!property) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) await store.uploadAttachment(property.id, file);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('inventory.modal.uploadFailed');
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!property) return;
    try {
      await store.deleteAttachment(property.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('inventory.modal.deleteFailed');
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }

  const currentProperty = $derived(
    property ? (store.properties.find((p) => p.id === property.id) ?? property) : null
  );
  const attachmentCount = $derived(currentProperty?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentProperty?.attachments ?? []).map((fname) => {
      const homeId = homesStore.activeHomeId;
      const url = apiUrl(`/api/homes/${homeId}/properties/${property!.id}/attachments/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );
</script>

<Modal open={true} title={isCreate ? `＋ ${$_('properties.modal.newProperty')}` : $_('properties.modal.editProperty')} {onclose} width="min(92vw, 820px)">
  <Tabs
    tabs={[
      { id: "info", label: $_('chores.editModal.info') },
      { id: "pros_cons", label: $_('properties.modal.prosCons') },
      { id: "notes", label: $_('works.modal.notes') },
      { id: "media", label: attachmentCount > 0 ? $_('chores.editModal.mediaCount', { values: { n: attachmentCount } }) : $_('chores.editModal.media'), disabled: isCreate },
    ]}
    active={activeTab}
    onchange={(id) => { activeTab = id as typeof activeTab; }}
  />

  {#if activeTab === "info"}
    <div class="row">
      <label>{$_('chores.editModal.emoji')}</label>
      <EmojiPicker bind:value={emoji} />
      <label style="margin-left:16px">{$_('chores.editModal.name')} *</label>
      <div class="flex-grow"><Input bind:value={name} placeholder={$_('properties.modal.namePlaceholder')} /></div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('properties.page.type')}</label>
        <select class="native-input" bind:value={type}>
          <option value="land">{$_('properties.modal.landOnly')}</option>
          <option value="house">{$_('properties.modal.existingHouse')}</option>
          <option value="new_build">{$_('properties.modal.newBuildOffPlan')}</option>
        </select>
      </div>
      <div class="row">
        <label>{$_('works.page.status')}</label>
        <select class="native-input" bind:value={status}>
          <option value="watching">{$_('properties.status.watching')}</option>
          <option value="visited">{$_('properties.status.visited')}</option>
          <option value="proposal_made">{$_('properties.status.proposalMade')}</option>
          <option value="purchased">{$_('properties.status.purchased')}</option>
          <option value="rejected">{$_('properties.status.rejected')}</option>
        </select>
      </div>
    </div>
    <div class="row">
      <label>{$_('properties.page.location')}</label>
      <select class="native-input" bind:value={locationId}>
        <option value="">{$_('works.modal.noneOption')}</option>
        {#each locationsStore.locations as loc}
          <option value={loc.id}>{loc.emoji} {loc.name}</option>
        {/each}
      </select>
    </div>
    <div class="row">
      <label>{$_('properties.modal.address')}</label>
      <div class="flex-grow"><Input bind:value={address} placeholder="Rua das Flores 12" /></div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('properties.modal.priceEur')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={price} placeholder="0.00" />
      </div>
      <div class="row">
        <label>{$_('properties.modal.listingUrl')}</label>
        <input class="native-input" type="url" bind:value={listingUrl} placeholder="https://…" />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('properties.modal.landSizeM2')}</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={landSize} placeholder="0" />
      </div>
      <div class="row">
        <label>{$_('properties.modal.builtSizeM2')}</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={builtSize} placeholder="0" />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('properties.modal.bedrooms')}</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={bedrooms} placeholder="0" />
      </div>
      <div class="row">
        <label>{$_('properties.modal.bathrooms')}</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={bathrooms} placeholder="0" />
      </div>
    </div>
    <div class="row">
      <label>{$_('properties.modal.agentContact')}</label>
      <div class="flex-grow"><Input bind:value={contact} placeholder="Maria Silva, Century21, +351 912 345 678" /></div>
    </div>
    {#if error}<div class="modal-error">{error}</div>{/if}
  {:else if activeTab === "pros_cons"}
    <div class="pros-cons-grid">
      <div class="pc-col">
        <div class="pc-label">{$_('properties.modal.pros')}</div>
        <ul class="pc-list">
          {#each pros as pro, i}
            <li><span>{pro}</span><button type="button" class="pc-remove" onclick={() => removePro(i)}>✕</button></li>
          {/each}
        </ul>
        <div class="pc-add">
          <input
            class="native-input"
            bind:value={newPro}
            placeholder={$_('properties.modal.addAPro')}
            onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addPro(); } }}
          />
          <Button variant="secondary" onclick={addPro}>{$_('common.add')}</Button>
        </div>
      </div>
      <div class="pc-col">
        <div class="pc-label">{$_('properties.modal.cons')}</div>
        <ul class="pc-list">
          {#each cons as con, i}
            <li><span>{con}</span><button type="button" class="pc-remove" onclick={() => removeCon(i)}>✕</button></li>
          {/each}
        </ul>
        <div class="pc-add">
          <input
            class="native-input"
            bind:value={newCon}
            placeholder={$_('properties.modal.addACon')}
            onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCon(); } }}
          />
          <Button variant="secondary" onclick={addCon}>{$_('common.add')}</Button>
        </div>
      </div>
    </div>
  {:else if activeTab === "notes"}
    <textarea class="native-input notes-area" bind:value={notes} placeholder={$_('inventory.modal.notesPlaceholder')} rows="10"></textarea>
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
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ {$_('works.modal.confirm')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 {$_('common.delete')}</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? $_('settings.security.saving') : isCreate ? $_('settings.security.create') : $_('common.save')}
    </Button>
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .flex-grow { flex: 1; min-width: 0; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .notes-area { resize: vertical; min-height: 160px; }

  .pros-cons-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .pc-col { display: flex; flex-direction: column; gap: 8px; }
  .pc-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .pc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .pc-list li {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 6px 10px; font-size: 12px; color: var(--text);
  }
  .pc-remove { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; padding: 0; }
  .pc-remove:hover { color: var(--danger); }
  .pc-add { display: flex; gap: 6px; }
  .pc-add .native-input { flex: 1; }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
