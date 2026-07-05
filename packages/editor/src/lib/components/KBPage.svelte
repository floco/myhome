<script lang="ts">
  import type { createKBStore, KBEntry } from "../kbStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type KBStore = ReturnType<typeof createKBStore>;
  interface Props {
    store: KBStore;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }
  let { store, selectedItemId = null, onclearselection }: Props = $props();

  let selectedId = $state<string | null>(null);
  let contentTab = $state<"content" | "media">("content");
  let editing = $state(false);
  let draftTitle = $state("");
  let draftContent = $state("");
  let confirmDelete = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let searchQuery = $state("");
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const filteredEntries = $derived(
    store.entries.filter((e) =>
      e.title.toLowerCase().includes(searchQuery.toLowerCase()),
    ),
  );

  const selectedEntry = $derived(
    selectedId ? (store.entries.find((e) => e.id === selectedId) ?? null) : null,
  );

  const mediaItems = $derived<MediaItem[]>(
    (selectedEntry?.attachments ?? []).map(fname => {
      const url = `/api/kb/${selectedId}/attachments/${fname}`;
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  function selectEntry(entry: KBEntry): void {
    selectedId = entry.id;
    draftTitle = entry.title;
    draftContent = entry.content;
    editing = false;
    confirmDelete = false;
    contentTab = "content";
    error = null;
  }

  $effect(() => {
    if (selectedItemId) {
      const found = store.entries.find((e) => e.id === selectedItemId);
      if (found) {
        selectEntry(found);
        onclearselection?.();
      }
    }
  });

  async function handleNew(): Promise<void> {
    try {
      const entry = await store.createEntry({ title: "New entry", content: "" });
      selectEntry(entry);
      editing = true;
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleSave(): Promise<void> {
    if (!selectedId) return;
    if (!draftTitle.trim()) { error = "Title cannot be empty"; return; }
    saving = true;
    error = null;
    try {
      await store.updateEntry(selectedId, {
        title: draftTitle.trim(),
        content: draftContent,
      });
      editing = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  function handleCancel(): void {
    if (selectedEntry) {
      draftTitle = selectedEntry.title;
      draftContent = selectedEntry.content;
    }
    editing = false;
    error = null;
  }

  async function handleDelete(): Promise<void> {
    if (!selectedId) return;
    try {
      await store.deleteEntry(selectedId);
      selectedId = null;
      editing = false;
      confirmDelete = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!selectedId) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await store.uploadAttachment(selectedId, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Upload failed"; }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!selectedId) return;
    try { await store.deleteAttachment(selectedId, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Delete failed"; }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
</script>

<div class="kb-page">
  <div class="kb-sidebar">
    <div class="sidebar-toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <Button onclick={handleNew}>＋ New</Button>
    </div>
    <div class="entry-list">
      {#each filteredEntries as entry (entry.id)}
        <div
          role="button"
          tabindex="0"
          class="entry-row"
          class:active={entry.id === selectedId}
          onclick={() => selectEntry(entry)}
          onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") selectEntry(entry); }}
        >
          <div class="entry-title">{entry.title}</div>
          <div class="entry-date">{fmtDate(entry.updatedAt)}</div>
        </div>
      {:else}
        <div class="list-empty">
          {searchQuery ? "No matching entries." : "No entries yet."}
        </div>
      {/each}
    </div>
  </div>

  <div class="kb-content">
    {#if !selectedEntry}
      <div class="content-empty">Select an entry or create one</div>
    {:else}
      <div class="content-header">
        <div class="content-header-left">
          {#if editing}
            <input class="title-input" bind:value={draftTitle} placeholder="Entry title" />
          {:else}
            <h1 class="content-title">{selectedEntry.title}</h1>
          {/if}
          <div class="content-tab-bar">
            <button class="content-tab" class:active={contentTab === "content"}
              onclick={() => { contentTab = "content"; }}>Content</button>
            <button class="content-tab" class:active={contentTab === "media"}
              onclick={() => { contentTab = "media"; editing = false; }}>
              Media{(selectedEntry.attachments?.length ?? 0) > 0 ? ` (${selectedEntry.attachments.length})` : ""}
            </button>
          </div>
        </div>
        <div class="header-actions">
          {#if contentTab === "content" && !editing}
            <Button variant="secondary" onclick={() => { editing = true; }}>Edit</Button>
          {/if}
          {#if confirmDelete}
            <span class="confirm-text">Delete?</span>
            <Button variant="danger" onclick={handleDelete}>✓</Button>
            <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
          {:else}
            <Button variant="ghost" onclick={() => { confirmDelete = true; }} title="Delete entry">🗑</Button>
          {/if}
        </div>
      </div>

      <div class="content-body">
        {#if contentTab === "content"}
          <MarkdownEditor
            bind:value={draftContent}
            bind:editing
            mediaItems={contentTab === "content" ? mediaItems : []}
            clickToEdit={false}
            placeholder="Start writing in Markdown…"
          />
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
      </div>

      {#if error}
        <div class="content-error">{error}</div>
      {/if}

      {#if editing && contentTab === "content"}
        <div class="content-footer">
          <Button variant="primary" disabled={saving} onclick={handleSave}>
            {saving ? "Saving…" : "Save"}
          </Button>
          <Button variant="secondary" onclick={handleCancel}>Cancel</Button>
        </div>
      {/if}
    {/if}
  </div>
</div>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .kb-page { display: flex; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .kb-sidebar {
    width: 260px; flex-shrink: 0;
    display: flex; flex-direction: column;
    border-right: 1px solid var(--border);
  }
  .sidebar-toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .sidebar-toolbar :global(.ui-input) { flex: 1; }

  .entry-list {
    flex: 1; overflow-y: auto; padding: var(--space-2);
    display: flex; flex-direction: column; gap: 2px;
  }
  .entry-row {
    padding: 8px 10px; border-radius: var(--radius-md);
    cursor: pointer; border-left: 3px solid transparent;
  }
  .entry-row:hover { background: var(--surface-hover); }
  .entry-row.active { background: var(--surface-alt); border-left-color: var(--accent); }
  .entry-title { font-size: 13px; color: var(--text); font-weight: 500; }
  .entry-date { font-size: 11px; color: var(--text-faint); margin-top: 2px; }
  .list-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 20px 0; }

  .kb-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .content-empty {
    flex: 1; display: flex; align-items: center; justify-content: center;
    color: var(--text-faint); font-size: 13px;
  }

  .content-header {
    display: flex; align-items: flex-start; gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .content-header-left { flex: 1; min-width: 0; }
  .content-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0 0 6px; }
  .title-input {
    width: 100%; background: var(--surface-alt); border: 1px solid var(--accent);
    border-radius: var(--radius-md); color: var(--text); box-sizing: border-box;
    font-size: 16px; font-weight: 600; padding: 6px 10px; font-family: var(--font-sans);
    margin-bottom: 6px;
  }
  .title-input:focus { outline: none; }
  .content-tab-bar { display: flex; }
  .content-tab {
    padding: 4px 12px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted); font-size: 11px; cursor: pointer; font-family: var(--font-sans);
  }
  .content-tab:hover { color: var(--text); }
  .content-tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .header-actions { display: flex; align-items: center; gap: var(--space-1); flex-shrink: 0; }
  .confirm-text { font-size: 11px; color: var(--danger); }

  .content-body {
    flex: 1; overflow: hidden; padding: var(--space-4);
    display: flex; flex-direction: column;
  }
  .content-body :global(.md-preview),
  .content-body :global(.md-editor) { flex: 1; }

  .content-error { padding: 0 var(--space-4); font-size: 11px; color: var(--danger); }
  .content-footer {
    display: flex; gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
</style>
