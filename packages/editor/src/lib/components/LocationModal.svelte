<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createLocationsStore, Location } from "../locationsStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;

  interface Props {
    location: Location | null;
    store: LocationsStore;
    onclose: () => void;
  }
  let { location, store, onclose }: Props = $props();

  const isCreate = location === null;

  let activeTab = $state<"info" | "notes" | "media">("info");
  let name = $state(location?.name ?? "");
  let emoji = $state(location?.emoji ?? "📍");
  let notes = $state(location?.notes ?? "");

  let editingNotes = $state(isCreate);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);

  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  async function handleSave(): Promise<void> {
    const trimmed = name.trim();
    if (!trimmed) return;
    saving = true; error = null;
    const patch = { name: trimmed, emoji, notes: notes.trim() };
    try {
      if (isCreate) {
        await store.createLocation(patch);
      } else {
        await store.updateLocation(location!.id, patch);
        editingNotes = false;
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('works.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!location) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) {
        await store.uploadAttachment(location.id, file);
      }
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('works.modal.uploadFailed');
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!location) return;
    try {
      await store.deleteAttachment(location.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('works.modal.deleteFailed');
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }

  const currentLocation = $derived(
    location ? (store.locations.find(l => l.id === location.id) ?? location) : null
  );
  const attachmentCount = $derived(currentLocation?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentLocation?.attachments ?? []).map(name => {
      const url = apiUrl(`/api/homes/${homesStore.activeHomeId}/attachments/locations/${location!.id}/${name}`);
      const isPdf = name.toLowerCase().endsWith(".pdf");
      return {
        id: name,
        name,
        url,
        thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url,
        type: isPdf ? "document" : "image",
      };
    })
  );
</script>

<Modal open={true} title={isCreate ? $_('locations.modal.addLocation') : $_('locations.modal.editLocation')} {onclose} width="min(92vw, 820px)">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "info"} onclick={() => { activeTab = "info"; }}>{$_('chores.editModal.info')}</button>
    <button class="tab" class:active={activeTab === "notes"} onclick={() => { activeTab = "notes"; }}>{$_('works.modal.notes')}</button>
    <button
      class="tab"
      class:active={activeTab === "media"}
      disabled={isCreate}
      onclick={() => { activeTab = "media"; }}
    >{$_('chores.editModal.media')}{attachmentCount > 0 ? ` (${attachmentCount})` : ""}</button>
  </div>

  {#if activeTab === "info"}
    <div class="row">
      <div class="field short">
        <label>{$_('locations.modal.flag')}</label>
        <EmojiPicker bind:value={emoji} flags={true} />
      </div>
      <div class="field grow">
        <label>{$_('chores.editModal.name')} *</label>
        <Input bind:value={name} placeholder={$_('locations.modal.namePlaceholder')} />
      </div>
    </div>
  {:else if activeTab === "notes"}
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder={$_('locations.modal.notesPlaceholder')}
      minHeight="260px"
    />
    {#if editingNotes && !isCreate}
      <Button variant="secondary" onclick={() => { editingNotes = false; }}>{$_('works.modal.doneEditing')}</Button>
    {/if}
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

  {#if error}<div class="modal-error">{error}</div>{/if}

  {#snippet footer()}
    <Button variant="ghost" onclick={onclose}>{$_('common.cancel')}</Button>
    <Button variant="primary" disabled={saving || !name.trim()} onclick={handleSave}>
      {saving ? $_('settings.security.saving') : isCreate ? $_('common.add') : $_('common.save')}
    </Button>
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab {
    padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans);
  }
  .tab:hover:not(:disabled) { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .tab:disabled { color: var(--text-faint); cursor: default; }

  .row { display: flex; gap: var(--space-2); margin-bottom: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field.grow { flex: 1; }
  .field.short { flex-shrink: 0; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
</style>
