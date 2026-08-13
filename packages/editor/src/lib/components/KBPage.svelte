<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createKBStore, KBEntry } from "../kbStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import { getStoredLastPageId, setStoredLastPageId, clearStoredLastPageId } from "../kbLastPage";
  import { setNavGuard } from "../navGuard";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";
  import KBTree from "./ui/KBTree.svelte";
  import KBTrash from "./ui/KBTrash.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";
  import Modal from "./ui/Modal.svelte";

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
  let confirmDelete = $state<{ id: string; title: string; count: number } | null>(null);
  let saveStatus = $state<"idle" | "pending" | "saving" | "saved" | "error">("idle");
  let error = $state<string | null>(null);
  let searchQuery = $state("");
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);
  let collapsedIds = $state<Set<string>>(new Set());
  let renamingId = $state<string | null>(null);
  let dragging = $state<string | null>(null);
  let trashDragOver = $state(false);
  let bookmarkModalOpen = $state(false);
  let bookmarkUrl = $state("");
  let bookmarkFetching = $state(false);
  let bookmarkError = $state<string | null>(null);
  let bookmarkResolve: ((html: string | null) => void) | null = null;
  let sidebarExpanded = $state(false);
  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  let savedStatusTimer: ReturnType<typeof setTimeout> | null = null;
  let inFlightSave: Promise<boolean> | null = null;

  const selectedEntry = $derived(
    selectedId ? (store.entries.find((e) => e.id === selectedId) ?? null) : null,
  );

  const mediaItems = $derived<MediaItem[]>(
    (selectedEntry?.attachments ?? []).map(fname => {
      const url = apiUrl(`/api/homes/${homesStore.activeHomeId}/attachments/kb/${selectedId}/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  let collapseDefaultApplied = $state(false);

  $effect(() => {
    if (collapseDefaultApplied) return;
    if (store.entries.length === 0) return;
    const parents = new Set(store.entries.filter((e) => e.parentId !== null).map((e) => e.parentId as string));
    collapsedIds = parents;
    collapseDefaultApplied = true;
  });

  function selectEntry(entry: KBEntry): void {
    selectedId = entry.id;
    draftTitle = entry.title;
    draftContent = entry.content;
    draftIcon = entry.icon;
    editing = false;
    confirmDelete = null;
    contentTab = "content";
    contentMode = "page";
    error = null;
    const homeId = homesStore.activeHomeId;
    if (homeId) setStoredLastPageId(homeId, entry.id);
  }

  // Set right before calling onnavigate() so the reconciliation effect below
  // can recognize the resulting selectedItemId prop update as an echo of our
  // own internal navigation (not a fresh external one) while it's in flight.
  let pendingNavigateId = $state<string | null>(null);

  async function navigate(entry: KBEntry): Promise<boolean> {
    const ok = await flushSave();
    if (!ok) return false;
    selectEntry(entry);
    pendingNavigateId = entry.id;
    onnavigate?.(entry.id);
    return true;
  }

  async function handleTreeSelect(entry: KBEntry): Promise<void> {
    await navigate(entry);
    sidebarExpanded = false;
  }

  // Reconciles the selectedItemId prop (sourced from the URL, e.g. deep
  // links, global search, browser back/forward) with local selection state.
  //
  // Internal navigation (handleNewPage, handleCreateChild, handleTreeSelect)
  // sets selectedId immediately via selectEntry(), then calls onnavigate()
  // to update the URL hash -- but the hashchange event, and therefore the
  // selectedItemId prop, only updates asynchronously afterward. In that gap,
  // any unrelated reactive re-run of this effect (e.g. triggered by
  // store.entries changing) would otherwise see a still-stale selectedItemId
  // that disagrees with the selectedId we just set, wrongly conclude the
  // user navigated elsewhere, and revert the selection -- clobbering the
  // editing=true the caller just set. pendingNavigateId suppresses
  // reconciliation for exactly that window, without preventing retries once
  // store.entries finishes loading on a fresh deep-linked page load (where
  // selectedItemId legitimately differs from selectedId and there's no
  // pending internal navigation to protect).
  $effect(() => {
    if (pendingNavigateId !== null) {
      if (selectedItemId === pendingNavigateId) pendingNavigateId = null;
      return;
    }
    if (selectedItemId && selectedItemId !== selectedId) {
      const found = store.entries.find((e) => e.id === selectedItemId);
      if (found) selectEntry(found);
    }
  });

  // On a bare "#/kb" open (no page id in the URL), redirect to whichever
  // page was last viewed in this browser for the active home, once entries
  // have actually loaded. Runs at most once per mount; a deep-linked
  // selectedItemId always wins and skips this entirely.
  let lastPageRedirectAttempted = $state(false);

  $effect(() => {
    if (lastPageRedirectAttempted) return;
    if (selectedItemId) { lastPageRedirectAttempted = true; return; }
    if (!store.loaded) return;
    lastPageRedirectAttempted = true;
    const homeId = homesStore.activeHomeId;
    if (!homeId) return;
    const storedId = getStoredLastPageId(homeId);
    if (!storedId) return;
    const found = store.entries.find((e) => e.id === storedId);
    if (found) {
      navigate(found);
    } else {
      clearStoredLastPageId(homeId);
    }
  });

  $effect(() => {
    setNavGuard(flushSave);
    return () => { setNavGuard(null); };
  });

  $effect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent): void {
      if (saveStatus === "pending" || saveStatus === "saving" || saveStatus === "error") {
        e.preventDefault();
        e.returnValue = "";
      }
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  });

  function resolveKbLink(id: string): { title: string; icon: string } | null {
    const found = store.entries.find((e) => e.id === id);
    return found ? { title: found.title, icon: found.icon } : null;
  }

  async function handleNewPage(): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    try {
      const entry = await store.createEntry({ title: $_('kb.page.newPageTitle'), content: "" });
      await navigate(entry);
      editing = true;
      sidebarExpanded = false;
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.createFailed');
    }
  }

  async function appendChildLink(parentId: string, child: { id: string; title: string }): Promise<void> {
    const parent = store.entries.find((e) => e.id === parentId);
    if (!parent) return;
    const link = `[${child.title}](#/kb/${child.id})`;
    await store.updateEntry(parentId, { content: `${parent.content}\n\n${link}\n` });
  }

  async function handleCreateChild(parentId: string): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    try {
      const entry = await store.createEntry({ title: $_('kb.page.newPageTitle'), content: "", parentId });
      await appendChildLink(parentId, entry);
      const next = new Set(collapsedIds);
      next.delete(parentId);
      collapsedIds = next;
      await navigate(entry);
      editing = true;
      sidebarExpanded = false;
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.createFailed');
    }
  }

  async function handleSlashPage(): Promise<{ id: string; title: string } | null> {
    if (!selectedId) return null;
    try {
      const entry = await store.createEntry({ title: $_('kb.page.newPageTitle'), content: "", parentId: selectedId });
      const next = new Set(collapsedIds);
      next.delete(selectedId);
      collapsedIds = next;
      return { id: entry.id, title: entry.title };
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.createFailed');
      return null;
    }
  }

  function handleInsertBookmark(): Promise<string | null> {
    bookmarkUrl = "";
    bookmarkError = null;
    bookmarkModalOpen = true;
    return new Promise((resolve) => { bookmarkResolve = resolve; });
  }

  function closeBookmarkModal(result: string | null): void {
    bookmarkModalOpen = false;
    bookmarkResolve?.(result);
    bookmarkResolve = null;
  }

  async function handleConfirmBookmark(): Promise<void> {
    const url = bookmarkUrl.trim();
    if (!url) { bookmarkError = $_('kb.page.bookmarkUrlRequired'); return; }
    bookmarkFetching = true;
    bookmarkError = null;
    try {
      const { html } = await store.fetchLinkPreview(url);
      closeBookmarkModal(html);
    } catch (e) {
      bookmarkError = e instanceof Error ? e.message : $_('kb.page.bookmarkFetchFailed');
    } finally {
      bookmarkFetching = false;
    }
  }

  function isDraftDirty(): boolean {
    if (!selectedEntry) return false;
    return draftTitle !== selectedEntry.title || draftContent !== selectedEntry.content;
  }

  $effect(() => {
    if (!editing || !isDraftDirty()) return;
    saveStatus = "pending";
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { flushSave(); }, 1200);
    return () => { if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; } };
  });

  async function flushSave(): Promise<boolean> {
    if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
    if (inFlightSave) {
      const ok = await inFlightSave;
      return ok ? flushSave() : false;
    }
    if (!isDraftDirty()) { saveStatus = "idle"; return true; }
    if (!selectedId) return true;
    if (!draftTitle.trim()) {
      error = $_('kb.page.titleEmpty');
      saveStatus = "error";
      return false;
    }
    saveStatus = "saving";
    error = null;
    const id = selectedId;
    const title = draftTitle.trim();
    const content = draftContent;
    const p = (async (): Promise<boolean> => {
      try {
        await store.updateEntry(id, { title, content });
        draftTitle = title;
        saveStatus = "saved";
        if (savedStatusTimer) clearTimeout(savedStatusTimer);
        savedStatusTimer = setTimeout(() => { saveStatus = "idle"; }, 2000);
        return true;
      } catch (e) {
        error = e instanceof Error ? e.message : $_('kb.page.saveFailed');
        saveStatus = "error";
        return false;
      } finally {
        inFlightSave = null;
      }
    })();
    inFlightSave = p;
    return p;
  }

  async function handleDoneEditing(): Promise<void> {
    const ok = await flushSave();
    if (ok) editing = false;
  }

  async function handleSwitchToMedia(): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    contentTab = "media";
    editing = false;
  }

  async function handleIconChange(icon: string): Promise<void> {
    if (!selectedId) return;
    try {
      await store.updateEntry(selectedId, { icon });
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.iconUpdateFailed');
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
    const entry = store.entries.find((e) => e.id === id);
    if (!entry) return;
    confirmDelete = { id, title: entry.title, count: childCount(id) + 1 };
  }

  async function handleConfirmDelete(): Promise<void> {
    if (!confirmDelete) return;
    const id = confirmDelete.id;
    try {
      await store.deleteEntry(id);
      if (selectedId && !store.entries.some((e) => e.id === selectedId)) {
        selectedId = null;
        editing = false;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : $_('chores.editModal.deleteFailed');
    } finally {
      confirmDelete = null;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!selectedId) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await store.uploadAttachment(selectedId, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : $_('chores.editModal.uploadFailed'); }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!selectedId) return;
    try { await store.deleteAttachment(selectedId, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : $_('chores.editModal.deleteFailed'); }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }

  function toggleTree(id: string): void {
    const next = new Set(collapsedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    collapsedIds = next;
  }

  const allParentsExpanded = $derived(
    store.entries.some((e) => e.parentId !== null) &&
    store.entries.filter((e) => e.parentId !== null).every((e) => !collapsedIds.has(e.parentId as string)),
  );

  function toggleAllTree(): void {
    if (allParentsExpanded) {
      collapsedIds = new Set(store.entries.filter((e) => e.parentId !== null).map((e) => e.parentId as string));
    } else {
      collapsedIds = new Set();
    }
  }

  async function handleRenamePage(id: string, title: string): Promise<void> {
    try {
      await store.updateEntry(id, { title });
      if (id === selectedId) draftTitle = title;
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.renameFailed');
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
        if (targetParentId) {
          await appendChildLink(targetParentId, dragged);
        }
      }
      if (orderedIds) {
        await store.reorderSiblings(targetParentId, orderedIds);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.moveFailed');
    }
  }

  function handleDropOnTrash(): void {
    const id = dragging;
    handleEndDrag();
    trashDragOver = false;
    if (id) handleAskDelete(id);
  }

  async function openTrash(): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    contentMode = "trash";
    selectedId = null;
    sidebarExpanded = false;
    try { await store.loadTrash(); }
    catch (e) { error = e instanceof Error ? e.message : $_('kb.page.loadTrashFailed'); }
  }

  async function handleRestore(id: string): Promise<void> {
    try { await store.restoreEntry(id); }
    catch (e) { error = e instanceof Error ? e.message : $_('kb.page.restoreFailed'); }
  }

  async function handlePermanentDelete(id: string): Promise<void> {
    try { await store.permanentlyDeleteEntry(id); }
    catch (e) { error = e instanceof Error ? e.message : $_('chores.editModal.deleteFailed'); }
  }

  async function handleEmptyTrash(): Promise<void> {
    try { await store.emptyTrash(); }
    catch (e) { error = e instanceof Error ? e.message : $_('kb.page.emptyTrashFailed'); }
  }
</script>

<div class="page">
<Card style="display:flex; padding:0; overflow:hidden; flex:1; min-height:0; font-family: var(--font-sans); position:relative;">
  {#if sidebarExpanded}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
    <div class="kb-backdrop" role="presentation" onclick={() => { sidebarExpanded = false; }}></div>
  {/if}
  <div class="kb-sidebar" class:expanded={sidebarExpanded}>
    <div class="sidebar-toolbar">
      <Input placeholder={$_('floorPlan.itemPicker.search')} bind:value={searchQuery} />
      <Button onclick={toggleAllTree} title={allParentsExpanded ? $_('kb.tree.collapseAll') : $_('kb.tree.expandAll')}>
        <span class="toggle-all-icon" class:open={allParentsExpanded}>▸</span>
      </Button>
      <Button onclick={handleNewPage} title={$_('kb.page.newPage')}>＋</Button>
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
    <button
      class="trash-link"
      class:drop-target={trashDragOver}
      onclick={openTrash}
      onpointermove={() => { if (dragging) trashDragOver = true; }}
      onpointerleave={() => { trashDragOver = false; }}
      onpointerup={() => { if (dragging) handleDropOnTrash(); }}
    >
      🗑 {$_('kb.trash.title')}{store.trash.length > 0 ? ` (${store.trash.length})` : ""}
    </button>
  </div>

  <div class="kb-content">
    <div class="kb-mobile-bar">
      <button
        class="kb-hamburger"
        onclick={() => { sidebarExpanded = !sidebarExpanded; }}
        title={sidebarExpanded ? $_('app.topbar.closeMenu') : $_('app.topbar.openMenu')}
      >{sidebarExpanded ? "✕" : "☰"}</button>
    </div>
    {#if contentMode === "trash"}
      <KBTrash
        entries={store.trash}
        onrestore={handleRestore}
        ondeleteforever={handlePermanentDelete}
        onemptytrash={handleEmptyTrash}
      />
    {:else if !selectedEntry}
      <div class="content-empty">{$_('kb.page.selectOrCreate')}</div>
    {:else}
      <div class="content-header">
        <div class="content-header-left">
          <div class="title-row">
            <EmojiPicker bind:value={draftIcon} onchange={handleIconChange} />
            {#if editing}
              <input class="title-input" bind:value={draftTitle} placeholder={$_('kb.page.pageTitlePlaceholder')} />
            {:else}
              <h1 class="content-title">{selectedEntry.title}</h1>
            {/if}
          </div>
          <div class="content-tab-bar">
            <button class="content-tab" class:active={contentTab === "content"}
              onclick={() => { contentTab = "content"; }}>{$_('kb.page.contentTab')}</button>
            <button class="content-tab" class:active={contentTab === "media"}
              onclick={handleSwitchToMedia}>
              {$_('chores.editModal.media')}{(selectedEntry.attachments?.length ?? 0) > 0 ? ` (${selectedEntry.attachments.length})` : ""}
            </button>
          </div>
        </div>
        <div class="header-actions">
          {#if contentTab === "content" && editing}
            <span
              class="save-status"
              class:save-status-saving={saveStatus === "saving" || saveStatus === "pending"}
              class:save-status-error={saveStatus === "error"}
              title={saveStatus === "saving" || saveStatus === "pending" ? $_('kb.page.saving') : saveStatus === "saved" ? $_('kb.page.saved') : saveStatus === "error" ? $_('kb.page.saveFailed') : undefined}
            >
              {#if saveStatus === "saving" || saveStatus === "pending"}↻
              {:else if saveStatus === "saved"}✓
              {:else if saveStatus === "error"}⚠
              {/if}
            </span>
            <Button variant="primary" onclick={handleDoneEditing} title={$_('works.modal.doneEditing')}>✓</Button>
          {:else if contentTab === "content" && !editing}
            <Button variant="ghost" onclick={() => { editing = true; }} title={$_('common.edit')}>✏</Button>
          {/if}
          <Button variant="ghost" onclick={() => handleAskDelete(selectedEntry.id)} title={$_('kb.page.deletePage')}>🗑</Button>
        </div>
      </div>

      <div class="content-body">
        {#if contentTab === "content"}
          <MarkdownEditor
            bind:value={draftContent}
            bind:editing
            mediaItems={contentTab === "content" ? mediaItems : []}
            clickToEdit={true}
            editTrigger="dblclick"
            placeholder={$_('kb.page.startWritingPlaceholder')}
            {resolveKbLink}
            onSlashPage={handleSlashPage}
            onInsertBookmark={handleInsertBookmark}
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
    {/if}
  </div>
</Card>
</div>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<Modal open={confirmDelete !== null} title={$_('kb.page.deletePageTitle')} onclose={() => { confirmDelete = null; }} width="420px">
  <p>
    {$_('kb.page.deletePrefix')} <strong>{confirmDelete?.title}</strong>{confirmDelete && confirmDelete.count > 1 ? ` ${$_('kb.page.andSubPages', { values: { n: confirmDelete.count - 1 } })}` : ""}?
    {confirmDelete && confirmDelete.count > 1 ? $_('kb.page.restoreThemNote') : $_('kb.page.restoreItNote')}
  </p>
  {#snippet footer()}
    <Button variant="ghost" onclick={() => { confirmDelete = null; }}>{$_('common.cancel')}</Button>
    <Button variant="danger" onclick={handleConfirmDelete}>{$_('common.delete')}</Button>
  {/snippet}
</Modal>

<Modal open={bookmarkModalOpen} title={$_('kb.page.bookmarkModalTitle')} onclose={() => closeBookmarkModal(null)} width="420px">
  <Input placeholder={$_('kb.page.bookmarkUrlPlaceholder')} bind:value={bookmarkUrl} />
  {#if bookmarkError}
    <p class="bookmark-error">{bookmarkError}</p>
  {/if}
  {#snippet footer()}
    <Button variant="ghost" onclick={() => closeBookmarkModal(null)}>{$_('common.cancel')}</Button>
    <Button variant="primary" disabled={bookmarkFetching} onclick={handleConfirmBookmark}>
      {bookmarkFetching ? $_('kb.page.bookmarkFetching') : $_('kb.page.bookmarkInsert')}
    </Button>
  {/snippet}
</Modal>

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

  .kb-backdrop {
    display: none;
  }

  @media (max-width: 700px) {
    .kb-backdrop {
      display: block;
      position: fixed; inset: 0; z-index: 19;
      background: rgba(0, 0, 0, 0.45);
    }
    .kb-sidebar {
      position: fixed; top: 48px; bottom: 0; left: 0; z-index: 20;
      width: 0; border-right: none;
      background: var(--surface); box-shadow: var(--shadow-lg);
      overflow: hidden; visibility: hidden;
      transition: width 0.18s ease;
    }
    .kb-sidebar.expanded { width: 260px; border-right: 1px solid var(--border); visibility: visible; }
  }

  .sidebar-toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .sidebar-toolbar :global(.ui-input) { flex: 1; }
  .toggle-all-icon {
    display: inline-block; font-size: 13px; line-height: 1;
    transition: transform 0.15s ease;
  }
  .toggle-all-icon.open { transform: rotate(90deg); }

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
  .trash-link.drop-target { background: color-mix(in srgb, var(--danger) 15%, transparent); color: var(--danger); }

  .kb-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

  .kb-mobile-bar { display: none; }

  @media (max-width: 700px) {
    .kb-mobile-bar {
      display: flex; align-items: center;
      padding: var(--space-2) var(--space-3);
      border-bottom: 1px solid var(--border); flex-shrink: 0;
    }
    .kb-hamburger {
      width: 32px; height: 32px;
      border: none; background: transparent; color: var(--text-muted);
      font-size: 16px; cursor: pointer; border-radius: var(--radius-sm);
      display: flex; align-items: center; justify-content: center;
    }
    .kb-hamburger:hover { background: var(--surface-hover); color: var(--text); }
  }

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

  .content-body {
    flex: 1; overflow: hidden; padding: var(--space-4);
    display: flex; flex-direction: column;
  }
  .content-body :global(.md-preview),
  .content-body :global(.md-editor) { flex: 1; }

  .content-error { padding: 0 var(--space-4); font-size: 11px; color: var(--danger); }

  .save-status { font-size: 13px; color: var(--text-muted); white-space: nowrap; display: inline-flex; align-items: center; }
  .save-status-saving { display: inline-block; animation: kb-spin 0.8s linear infinite; }
  .save-status-error { color: var(--danger); }

  @keyframes kb-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .bookmark-error { color: var(--danger); font-size: 12px; margin: 6px 0 0; }
</style>
