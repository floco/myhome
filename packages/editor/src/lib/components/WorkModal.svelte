<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    work: Work | null;
    store: WorksStore;
    settingsStore: SettingsStore;
    onclose: () => void;
    onplaceonmap?: (workId: string) => void;
  }

  let { work, store, settingsStore, onclose, onplaceonmap }: Props = $props();

  const isCreate = work === null;

  let activeTab = $state<"info" | "notes" | "media">("info");
  let title = $state(work?.title ?? "");
  let description = $state(work?.description ?? "");
  let status = $state<Work["status"]>(work?.status ?? "planned");
  let categoryId = $state(work?.categoryId ?? "");
  let date = $state(work?.date ?? new Date().toISOString().slice(0, 10));
  let totalCost = $state<string>(work?.totalCost != null ? String(work.totalCost) : "");
  let supplierId = $state(work?.supplierId ?? "");
  let notes = $state(work?.notes ?? "");

  let editingNotes = $state(isCreate);
  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);

  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  async function handleSave(): Promise<void> {
    if (!title.trim()) { error = $_('works.modal.titleRequired'); return; }
    if (!date) { error = $_('costs.entryModal.dateRequired'); return; }
    saving = true; error = null;
    const patch = {
      title: title.trim(),
      description: description.trim(),
      status,
      categoryId: categoryId || null,
      date,
      totalCost: totalCost ? parseFloat(totalCost) || null : null,
      supplierId: supplierId || null,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createWork(patch);
        onclose();
      } else {
        await store.updateWork(work!.id, patch);
        editingNotes = false;
        onclose();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : $_('works.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!work) return;
    deleting = true;
    try {
      await store.deleteWork(work.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('works.modal.deleteFailed');
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!work) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) {
        await store.uploadAttachment(work.id, file);
      }
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('works.modal.uploadFailed');
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!work) return;
    try {
      await store.deleteAttachment(work.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('works.modal.deleteFailed');
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }

  const currentWork = $derived(
    work ? (store.works.find(w => w.id === work.id) ?? work) : null
  );
  const attachmentCount = $derived(currentWork?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentWork?.attachments ?? []).map(name => {
      const url = apiUrl(`/api/works/${work!.id}/attachments/${name}`);
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

<Modal open={true} title={isCreate ? `＋ ${$_('works.modal.newWork')}` : $_('works.modal.editWork')} {onclose} width="min(92vw, 820px)">
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
      <label>{$_('works.page.title')} *</label>
      <Input bind:value={title} placeholder={$_('works.modal.workTitlePlaceholder')} />
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('costs.page.category')}</label>
        <select class="native-input" bind:value={categoryId}>
          <option value="">{$_('works.modal.noneOption')}</option>
          {#each settingsStore.workCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
      <div class="row">
        <label>{$_('works.page.status')}</label>
        <select class="native-input" bind:value={status}>
          <option value="planned">{$_('works.status.planned')}</option>
          <option value="in_progress">{$_('works.status.inProgress')}</option>
          <option value="done">{$_('works.status.done')}</option>
        </select>
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('costs.entryModal.date')} *</label>
        <DatePicker bind:value={date} />
      </div>
      <div class="row">
        <label>{$_('works.modal.totalCostEur')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={totalCost} placeholder="0.00" />
      </div>
    </div>
    <div class="row">
      <label>{$_('costs.entryModal.supplier')}</label>
      <select class="native-input" bind:value={supplierId}>
        <option value="">{$_('works.modal.noneOption')}</option>
        {#each settingsStore.suppliers as s}
          <option value={s.id}>{s.name}</option>
        {/each}
      </select>
    </div>
    <div class="row">
      <label>{$_('works.modal.description')}</label>
      <textarea class="native-input desc-area" bind:value={description} placeholder={$_('works.modal.descriptionPlaceholder')} rows="2"></textarea>
    </div>
  {:else if activeTab === "notes"}
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder={$_('works.modal.notesPlaceholder')}
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
    {#if onplaceonmap && !isCreate}
      <Button variant="secondary" onclick={() => { onplaceonmap(work!.id); onclose(); }}>📍 {$_('chores.editModal.placeOnMap')}</Button>
    {/if}
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? $_('settings.security.saving') : isCreate ? $_('settings.security.create') : $_('common.save')}
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

  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .desc-area { resize: vertical; min-height: 48px; }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
