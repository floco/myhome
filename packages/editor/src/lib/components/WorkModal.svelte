<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";

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

  let activeTab = $state<"info" | "notes" | "attachments">("info");
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

  async function handleSave(): Promise<void> {
    if (!title.trim()) { error = "Title is required"; return; }
    if (!date) { error = "Date is required"; return; }
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
      error = e instanceof Error ? e.message : "Save failed";
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
      error = e instanceof Error ? e.message : "Delete failed";
      deleting = false;
    }
  }

  async function handleUpload(e: Event): Promise<void> {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !work) return;
    uploading = true; uploadError = null;
    try {
      await store.uploadAttachment(work.id, file);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Upload failed";
    } finally {
      uploading = false;
      input.value = "";
    }
  }

  async function handleDeleteAttachment(filename: string): Promise<void> {
    if (!work) return;
    try {
      await store.deleteAttachment(work.id, filename);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Delete failed";
    }
  }

  const currentWork = $derived(
    work ? (store.works.find(w => w.id === work.id) ?? work) : null
  );
  const attachmentCount = $derived(currentWork?.attachments.length ?? 0);
</script>

<Modal open={true} title={isCreate ? "＋ New work" : "Edit work"} {onclose} width="min(92vw, 820px)">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "info"} onclick={() => { activeTab = "info"; }}>Info</button>
    <button class="tab" class:active={activeTab === "notes"} onclick={() => { activeTab = "notes"; }}>Notes</button>
    <button
      class="tab"
      class:active={activeTab === "attachments"}
      disabled={isCreate}
      onclick={() => { activeTab = "attachments"; }}
    >Attachments{attachmentCount > 0 ? ` (${attachmentCount})` : ""}</button>
  </div>

  {#if activeTab === "info"}
    <div class="row">
      <label>Title *</label>
      <Input bind:value={title} placeholder="Work title" />
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Category</label>
        <select class="native-input" bind:value={categoryId}>
          <option value="">— None —</option>
          {#each settingsStore.workCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
      <div class="row">
        <label>Status</label>
        <select class="native-input" bind:value={status}>
          <option value="planned">Planned</option>
          <option value="in_progress">In progress</option>
          <option value="done">Done</option>
        </select>
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Date *</label>
        <DatePicker bind:value={date} />
      </div>
      <div class="row">
        <label>Total cost (€)</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={totalCost} placeholder="0.00" />
      </div>
    </div>
    <div class="row">
      <label>Supplier</label>
      <select class="native-input" bind:value={supplierId}>
        <option value="">— None —</option>
        {#each settingsStore.suppliers as s}
          <option value={s.id}>{s.name}</option>
        {/each}
      </select>
    </div>
    <div class="row">
      <label>Description</label>
      <textarea class="native-input desc-area" bind:value={description} placeholder="Short summary of the work…" rows="2"></textarea>
    </div>
  {:else if activeTab === "notes"}
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder="Click to add markdown notes…"
      minHeight="260px"
    />
    {#if editingNotes && !isCreate}
      <Button variant="secondary" onclick={() => { editingNotes = false; }}>Done editing</Button>
    {/if}
  {:else}
    <div class="attachments">
      {#if currentWork && currentWork.attachments.length > 0}
        {#each currentWork.attachments as filename}
          <div class="attach-row">
            <span class="attach-icon">📄</span>
            <a class="attach-name" href="/api/works/{work!.id}/attachments/{filename}" target="_blank" rel="noopener">{filename}</a>
            <button class="attach-del" onclick={() => handleDeleteAttachment(filename)} title="Delete">✕</button>
          </div>
        {/each}
      {:else}
        <div class="attach-empty">No attachments yet.</div>
      {/if}
      <label class="upload-btn" class:uploading>
        {uploading ? "Uploading…" : "＋ Upload PDF"}
        <input type="file" accept=".pdf" style="display:none" onchange={handleUpload} />
      </label>
      {#if uploadError}<div class="upload-error">{uploadError}</div>{/if}
    </div>
  {/if}

  {#if error}<div class="modal-error">{error}</div>{/if}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ Confirm</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    {#if onplaceonmap && !isCreate}
      <Button variant="secondary" onclick={() => { onplaceonmap(work!.id); onclose(); }}>📍 Place on map</Button>
    {/if}
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? "Saving…" : isCreate ? "Create" : "Save"}
    </Button>
  {/snippet}
</Modal>

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

  .attachments { display: flex; flex-direction: column; gap: 6px; }
  .attach-row {
    display: flex; align-items: center; gap: 8px;
    background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .attach-icon { font-size: 14px; }
  .attach-name { flex: 1; font-size: 11px; color: var(--accent); text-decoration: none; }
  .attach-name:hover { text-decoration: underline; }
  .attach-del { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; }
  .attach-del:hover { color: var(--danger); }
  .attach-empty { font-size: 11px; color: var(--text-faint); text-align: center; padding: 12px 0; }
  .upload-btn {
    background: var(--surface-alt); border: 1px dashed var(--border); color: var(--text-muted);
    padding: 7px 12px; border-radius: var(--radius-md); font-size: 11px; cursor: pointer;
    text-align: center; font-family: var(--font-sans); display: block;
  }
  .upload-btn:hover:not(.uploading) { background: var(--surface-hover); color: var(--text); }
  .upload-btn.uploading { color: var(--text-faint); cursor: default; }
  .upload-error { font-size: 10px; color: var(--danger); }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
