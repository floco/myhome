<!-- packages/editor/src/lib/components/WorkModal.svelte -->
<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import DatePicker from "./DatePicker.svelte";

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
      } else {
        await store.updateWork(work!.id, patch);
      }
      onclose();
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

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="overlay" onclick={(e) => { if (e.target === e.currentTarget) onclose(); }}>
  <div class="modal">
    <div class="modal-header">
      <h2>{isCreate ? "＋ New work" : "Edit work"}</h2>
      <button class="close-btn" onclick={onclose}>✕</button>
    </div>

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

    <div class="modal-body">
      {#if activeTab === "info"}
        <div class="row">
          <label>Title *</label>
          <input class="flex-input" bind:value={title} placeholder="Work title" />
        </div>
        <div class="row-pair">
          <div class="row">
            <label>Category</label>
            <select class="flex-input" bind:value={categoryId}>
              <option value="">— None —</option>
              {#each settingsStore.workCategories as cat}
                <option value={cat.id}>{cat.emoji} {cat.name}</option>
              {/each}
            </select>
          </div>
          <div class="row">
            <label>Status</label>
            <select class="flex-input" bind:value={status}>
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
            <input class="flex-input" type="number" min="0" step="0.01" bind:value={totalCost} placeholder="0.00" />
          </div>
        </div>
        <div class="row">
          <label>Supplier</label>
          <select class="flex-input" bind:value={supplierId}>
            <option value="">— None —</option>
            {#each settingsStore.suppliers as s}
              <option value={s.id}>{s.name}</option>
            {/each}
          </select>
        </div>
        <div class="row">
          <label>Description</label>
          <textarea class="flex-input desc-area" bind:value={description} placeholder="Short summary of the work…" rows="2"></textarea>
        </div>
      {:else if activeTab === "notes"}
        <textarea class="flex-input notes-area" bind:value={notes} placeholder="Markdown notes…"></textarea>
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
    </div>

    {#if error}<div class="modal-error">{error}</div>{/if}

    <div class="modal-footer">
      {#if !isCreate}
        {#if confirmDelete}
          <span class="confirm-text">Delete?</span>
          <button class="danger-btn" onclick={handleDelete} disabled={deleting}>✓ Confirm</button>
          <button class="cancel-btn" onclick={() => { confirmDelete = false; }}>✕</button>
        {:else}
          <button class="danger-btn" onclick={() => { confirmDelete = true; }}>🗑 Delete</button>
        {/if}
      {/if}
      <span class="spacer"></span>
      {#if onplaceonmap && !isCreate}
        <button class="place-btn" onclick={() => { onplaceonmap(work!.id); onclose(); }}>📍 Place on map</button>
      {/if}
      <button class="save-btn" onclick={handleSave} disabled={saving}>
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

  .tabs { display: flex; border-bottom: 1px solid #2a2a4a; flex-shrink: 0; }
  .tab {
    padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
    color: #556; font-size: 12px; cursor: pointer; font-family: sans-serif;
  }
  .tab:hover:not(:disabled) { color: #99a; }
  .tab.active { border-bottom-color: #5566cc; color: #aaf; }
  .tab:disabled { color: #334; cursor: default; }

  .modal-body {
    padding: 16px 18px; overflow-y: auto; flex: 1;
    font-family: sans-serif; display: flex; flex-direction: column; gap: 10px;
  }
  .row { display: flex; flex-direction: column; gap: 4px; }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  label { font-size: 10px; color: #445; text-transform: uppercase; letter-spacing: .06em; }
  .flex-input {
    background: #111128; border: 1px solid #2a2a4a; color: #ccc;
    padding: 6px 8px; border-radius: 4px; font-size: 12px; font-family: sans-serif;
    width: 100%; box-sizing: border-box;
  }
  .flex-input:focus { outline: 1px solid #5566cc; border-color: #5566cc; }
  select.flex-input { cursor: pointer; }
  .desc-area { resize: vertical; min-height: 48px; }
  .notes-area { resize: none; min-height: 260px; font-family: monospace; font-size: 12px; line-height: 1.5; flex: 1; }

  .attachments { display: flex; flex-direction: column; gap: 6px; }
  .attach-row {
    display: flex; align-items: center; gap: 8px;
    background: #111128; border: 1px solid #2a2a4a; border-radius: 4px; padding: 6px 10px;
  }
  .attach-icon { font-size: 14px; }
  .attach-name { flex: 1; font-size: 11px; color: #88aaff; text-decoration: none; }
  .attach-name:hover { text-decoration: underline; }
  .attach-del { background: none; border: none; color: #446; cursor: pointer; font-size: 12px; }
  .attach-del:hover { color: #f44; }
  .attach-empty { font-size: 11px; color: #334; text-align: center; padding: 12px 0; }
  .upload-btn {
    background: #1a1a2e; border: 1px dashed #2a2a4a; color: #556;
    padding: 7px 12px; border-radius: 4px; font-size: 11px; cursor: pointer;
    text-align: center; font-family: sans-serif; display: block;
  }
  .upload-btn:hover:not(.uploading) { background: #2a2a4a; color: #99a; }
  .upload-btn.uploading { color: #334; cursor: default; }
  .upload-error { font-size: 10px; color: #f88; }

  .modal-error {
    padding: 4px 18px; font-size: 11px; color: #f88;
    background: #2a1a1a; border-top: 1px solid #4a2a2a; flex-shrink: 0;
  }
  .modal-footer {
    display: flex; align-items: center; gap: 8px; padding: 12px 18px;
    border-top: 1px solid #2a2a4a; flex-shrink: 0; font-family: sans-serif;
  }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: #f88; }
  .danger-btn {
    background: #2a1a1a; border: 1px solid #4a2a2a; color: #f88;
    padding: 5px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;
  }
  .danger-btn:hover:not(:disabled) { background: #3a1a1a; }
  .cancel-btn {
    background: none; border: 1px solid #2a2a4a; color: #667;
    padding: 5px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;
  }
  .place-btn {
    background: #1e2a4a; border: 1px solid #3a4a8a; color: #aac;
    padding: 5px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;
  }
  .place-btn:hover { background: #2a3a6a; }
  .save-btn {
    background: #3344aa; color: #ccf; border: none;
    padding: 5px 16px; border-radius: 4px; font-size: 12px; cursor: pointer;
  }
  .save-btn:hover:not(:disabled) { background: #4455bb; }
  .save-btn:disabled { opacity: .5; cursor: default; }
</style>
