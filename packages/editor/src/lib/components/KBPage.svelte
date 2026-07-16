<script lang="ts">
  import type { createKBStore, KBEntry } from "../kbStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";
  import KBTree from "./ui/KBTree.svelte";
  import KBTrash from "./ui/KBTrash.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type KBStore = ReturnType<typeof createKBStore>;
  interface Props {
    store: KBStore;
    selectedItemId?: string | null;
    onnavigate?: (id: string) => void;
  }
  let { store, selectedItemId = null, onnavigate }: Props = $props();

  let selectedId = $state<string | null>(null);
  let contentMode = $state<"page" | "trash">("page");
  let contentTab = $state<"content" | "media">("content");
  let editing = $state(false);
  let draftTitle = $state("");
  let draftContent = $state("");
  let draftIcon = $state("📄");
  let confirmDelete = $state<{ count: number } | null>(null);
  let pendingDeleteId = $state<string | null>(null);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let searchQuery = $state("");
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);
  let collapsedIds = $state<Set<string>>(new Set());
  let renamingId = $state<string | null>(null);
  let dragging = $state<string | null>(null);

  const selectedEntry = $derived(
    selectedId ? (store.entries.find((e) => e.id === selectedId) ?? null) : null,
  );

  const mediaItems = $derived<MediaItem[]>(
    (selectedEntry?.attachments ?? []).map(fname => {
      const url = apiUrl(`/api/kb/${selectedId}/attachments/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  function selectEntry(entry: KBEntry): void {
    selectedId = entry.id;
    draftTitle = entry.title;
    draftContent = entry.content;
    draftIcon = entry.icon;
    editing = false;
    confirmDelete = null;
    pendingDeleteId = null;
    contentTab = "content";
    contentMode = "page";
    error = null;
  }

  function handleTreeSelect(entry: KBEntry): void {
    selectEntry(entry);
    onnavigate?.(entry.id);
  }

  $effect(() => {
    if (selectedItemId && selectedItemId !== selectedId) {
      const found = store.entries.find((e) => e.id === selectedItemId);
      if (found) selectEntry(found);
    }
  });

  function resolveKbLink(id: string): { title: string; icon: string } | null {
    const found = store.entries.find((e) => e.id === id);
    return found ? { title: found.title, icon: found.icon } : null;
  }

  async function handleNewPage(): Promise<void> {
    try {
      const entry = await store.createEntry({ title: "New page", content: "" });
      selectEntry(entry);
      editing = true;
      onnavigate?.(entry.id);
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleCreateChild(parentId: string): Promise<void> {
    try {
      const parent = store.entries.find((e) => e.id === parentId);
      const entry = await store.createEntry({ title: "New page", content: "", parentId });
      if (parent) {
        const link = `[${entry.title}](#/kb/${entry.id})`;
        await store.updateEntry(parentId, { content: `${parent.content}\n\n${link}\n` });
      }
      const next = new Set(collapsedIds);
      next.delete(parentId);
      collapsedIds = next;
      selectEntry(entry);
      editing = true;
      onnavigate?.(entry.id);
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleSlashPage(): Promise<{ id: string; title: string } | null> {
    if (!selectedId) return null;
    try {
      const entry = await store.createEntry({ title: "New page", content: "", parentId: selectedId });
      const next = new Set(collapsedIds);
      next.delete(selectedId);
      collapsedIds = next;
      return { id: entry.id, title: entry.title };
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
      return null;
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

  async function handleIconChange(icon: string): Promise<void> {
    if (!selectedId) return;
    try {
      await store.updateEntry(selectedId, { icon });
    } catch (e) {
      error = e instanceof Error ? e.message : "Icon update failed";
    }
  }

  function childCount(id: string): number {
    let count = 0;
    const stack = [id];
    while (stack.length) {
      const current = stack.pop()!;
      for (const e of store.entries) {
        if (e.parentId === current) { count += 1; stack.push(e.id); }
      }
    }
    return count;
  }

  function handleAskDelete(id: string): void {
    pendingDeleteId = id;
    confirmDelete = { count: childCount(id) + 1 };
  }

  async function handleConfirmDelete(): Promise<void> {
    const id = pendingDeleteId;
    if (!id) return;
    try {
      await store.deleteEntry(id);
      if (selectedId && !store.entries.some((e) => e.id === selectedId)) {
        selectedId = null;
        editing = false;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
    } finally {
      confirmDelete = null;
      pendingDeleteId = null;
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

  function toggleTree(id: string): void {
    const next = new Set(collapsedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    collapsedIds = next;
  }

  async function handleRenamePage(id: string, title: string): Promise<void> {
    try {
      await store.updateEntry(id, { title });
      if (id === selectedId) draftTitle = title;
    } catch (e) {
      error = e instanceof Error ? e.message : "Rename failed";
    } finally {
      renamingId = null;
    }
  }

  function handleCancelRename(): void {
    renamingId = null;
  }

  function handleStartDrag(id: string): void {
    dragging = id;
  }

  function handleEndDrag(): void {
    dragging = null;
  }

  async function handleTreeDrop(
    draggedId: string, targetParentId: string | null, orderedIds: string[] | null,
  ): Promise<void> {
    try {
      const dragged = store.entries.find((e) => e.id === draggedId);
      if (dragged && dragged.parentId !== targetParentId) {
        await store.updateEntry(draggedId, { parentId: targetParentId });
      }
      if (orderedIds) {
        await store.reorderSiblings(targetParentId, orderedIds);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Move failed";
    }
  }

  async function openTrash(): Promise<void> {
    contentMode = "trash";
    selectedId = null;
    try { await store.loadTrash(); }
    catch (e) { error = e instanceof Error ? e.message : "Failed to load trash"; }
  }

  async function handleRestore(id: string): Promise<void> {
    try { await store.restoreEntry(id); }
    catch (e) { error = e instanceof Error ? e.message : "Restore failed"; }
  }

  async function handlePermanentDelete(id: string): Promise<void> {
    try { await store.permanentlyDeleteEntry(id); }
    catch (e) { error = e instanceof Error ? e.message : "Delete failed"; }
  }

  async function handleEmptyTrash(): Promise<void> {
    try { await store.emptyTrash(); }
    catch (e) { error = e instanceof Error ? e.message : "Empty trash failed"; }
  }
</script>

<div class="page">
<Card style="display:flex; padding:0; overflow:hidden; flex:1; min-height:0; font-family: var(--font-sans);">
  <div class="kb-sidebar">
    <div class="sidebar-toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <Button onclick={handleNewPage}>＋ New Page</Button>
    </div>
    <div class="entry-list">
      <KBTree
        entries={store.entries}
        {selectedId}
        {searchQuery}
        {collapsedIds}
        {renamingId}
        {dragging}
        onselect={handleTreeSelect}
        ontoggle={toggleTree}
        oncreatechild={handleCreateChild}
        onstartrename={(id) => { renamingId = id; }}
        oncommitrename={handleRenamePage}
        oncancelrename={handleCancelRename}
        ondelete={handleAskDelete}
        onstartdrag={handleStartDrag}
        onenddrag={handleEndDrag}
        ondrop={handleTreeDrop}
      />
    </div>
    <button class="trash-link" onclick={openTrash}>
      🗑 Trash{store.trash.length > 0 ? ` (${store.trash.length})` : ""}
    </button>
  </div>

  <div class="kb-content">
    {#if contentMode === "trash"}
      <KBTrash
        entries={store.trash}
        onrestore={handleRestore}
        ondeleteforever={handlePermanentDelete}
        onemptytrash={handleEmptyTrash}
      />
    {:else if !selectedEntry}
      <div class="content-empty">Select a page or create one</div>
    {:else}
      <div class="content-header">
        <div class="content-header-left">
          <div class="title-row">
            <EmojiPicker bind:value={draftIcon} onchange={handleIconChange} />
            {#if editing}
              <input class="title-input" bind:value={draftTitle} placeholder="Page title" />
            {:else}
              <h1 class="content-title">{selectedEntry.title}</h1>
            {/if}
          </div>
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
          {#if confirmDelete && pendingDeleteId === selectedEntry.id}
            <span class="confirm-text">
              Delete{confirmDelete.count > 1 ? ` this and ${confirmDelete.count - 1} sub-page${confirmDelete.count > 2 ? "s" : ""}` : ""}?
            </span>
            <Button variant="danger" onclick={handleConfirmDelete}>✓</Button>
            <Button variant="ghost" onclick={() => { confirmDelete = null; pendingDeleteId = null; }}>✕</Button>
          {:else}
            <Button variant="ghost" onclick={() => handleAskDelete(selectedEntry.id)} title="Delete page">🗑</Button>
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
            placeholder="Start writing in Markdown… (type /page to create a linked child page)"
            {resolveKbLink}
            onSlashPage={handleSlashPage}
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
</Card>
</div>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .page {
    display: flex; height: 100%; box-sizing: border-box;
    padding: var(--space-4); background: var(--bg);
  }

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

  .trash-link {
    flex-shrink: 0; text-align: left; padding: 8px 12px;
    background: none; border: none; border-top: 1px solid var(--border);
    color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans);
  }
  .trash-link:hover { background: var(--surface-hover); color: var(--text); }

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
  .title-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: 6px; }
  .content-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0; }
  .title-input {
    flex: 1; min-width: 0; background: var(--surface-alt); border: 1px solid var(--accent);
    border-radius: var(--radius-md); color: var(--text); box-sizing: border-box;
    font-size: 16px; font-weight: 600; padding: 6px 10px; font-family: var(--font-sans);
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
