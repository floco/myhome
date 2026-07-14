<!-- packages/editor/src/lib/components/ui/KBTree.svelte -->
<script lang="ts">
  import type { KBEntry, KBFolder } from "../../kbStore.svelte";
  import Self from "./KBTree.svelte";

  interface Dragging {
    kind: "entry" | "folder";
    id: string;
  }

  interface Props {
    folders: KBFolder[];
    entries: KBEntry[];
    parentId?: string | null;
    depth?: number;
    selectedId: string | null;
    searchQuery: string;
    collapsedIds: Set<string>;
    renamingFolderId: string | null;
    dragging: Dragging | null;
    onselectentry: (entry: KBEntry) => void;
    ontogglefolder: (folderId: string) => void;
    oncreatesubfolder: (parentId: string) => void;
    oncreateentryin: (folderId: string) => void;
    onstartrename: (folderId: string) => void;
    oncommitrename: (folderId: string, name: string) => void;
    oncancelrename: () => void;
    ondeletefolder: (folderId: string) => void;
    onstartdrag: (kind: "entry" | "folder", id: string) => void;
    onenddrag: () => void;
    ondropon: (targetFolderId: string | null) => void;
  }

  let {
    folders, entries, parentId = null, depth = 0, selectedId, searchQuery, collapsedIds,
    renamingFolderId, dragging,
    onselectentry, ontogglefolder, oncreatesubfolder, oncreateentryin,
    onstartrename, oncommitrename, oncancelrename, ondeletefolder,
    onstartdrag, onenddrag, ondropon,
  }: Props = $props();

  let renameDraft = $state("");
  let menuOpenFor = $state<string | null>(null);
  let dragOverId = $state<string | null>(null);

  function matches(text: string): boolean {
    const q = searchQuery.trim().toLowerCase();
    return !q || text.toLowerCase().includes(q);
  }

  const visibleFolderIds = $derived.by(() => {
    const q = searchQuery.trim();
    if (!q) return null;
    const childFoldersOf = new Map<string | null, KBFolder[]>();
    for (const f of folders) {
      const list = childFoldersOf.get(f.parentId) ?? [];
      list.push(f);
      childFoldersOf.set(f.parentId, list);
    }
    const childEntriesOf = new Map<string | null, KBEntry[]>();
    for (const e of entries) {
      const list = childEntriesOf.get(e.folderId) ?? [];
      list.push(e);
      childEntriesOf.set(e.folderId, list);
    }
    const visible = new Set<string>();
    function visit(folder: KBFolder): boolean {
      const ownMatch = matches(folder.name);
      const hasMatchingEntry = (childEntriesOf.get(folder.id) ?? []).some((e) => matches(e.title));
      const hasMatchingChild = (childFoldersOf.get(folder.id) ?? []).map(visit).some(Boolean);
      const keep = ownMatch || hasMatchingEntry || hasMatchingChild;
      if (keep) visible.add(folder.id);
      return keep;
    }
    for (const f of childFoldersOf.get(null) ?? []) visit(f);
    return visible;
  });

  const childFolders = $derived(
    folders
      .filter((f) => f.parentId === parentId)
      .filter((f) => visibleFolderIds === null || visibleFolderIds.has(f.id))
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name)),
  );
  const childEntries = $derived(
    entries
      .filter((e) => e.folderId === parentId)
      .filter((e) => matches(e.title))
      .slice()
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt)),
  );

  function isOpen(folderId: string): boolean {
    return searchQuery.trim() !== "" || !collapsedIds.has(folderId);
  }

  function hasChildren(folderId: string): boolean {
    return folders.some((f) => f.parentId === folderId) || entries.some((e) => e.folderId === folderId);
  }

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function startRename(folder: KBFolder): void {
    renameDraft = folder.name;
    menuOpenFor = null;
    onstartrename(folder.id);
  }

  function commitRename(folderId: string): void {
    const name = renameDraft.trim();
    if (name) oncommitrename(folderId, name);
    else oncancelrename();
  }

  function wouldCreateCycle(folderId: string, targetId: string): boolean {
    if (folderId === targetId) return true;
    let current: string | null = targetId;
    const seen = new Set<string>();
    while (current !== null) {
      if (current === folderId) return true;
      if (seen.has(current)) return false;
      seen.add(current);
      const f = folders.find((x) => x.id === current);
      current = f ? f.parentId : null;
    }
    return false;
  }

  function canDropOnFolder(targetId: string): boolean {
    if (!dragging) return false;
    if (dragging.kind === "folder" && wouldCreateCycle(dragging.id, targetId)) return false;
    return true;
  }
</script>

<ul class="kb-tree" class:root={depth === 0}>
  {#each childFolders as folder (folder.id)}
    <li>
      <div
        class="tree-row folder-row"
        class:drop-target={dragOverId === folder.id}
        draggable="true"
        role="treeitem"
        aria-expanded={isOpen(folder.id)}
        tabindex="0"
        ondragstart={(e) => { e.dataTransfer?.setData("text/plain", ""); onstartdrag("folder", folder.id); }}
        ondragend={onenddrag}
        ondragover={(e) => { if (canDropOnFolder(folder.id)) { e.preventDefault(); dragOverId = folder.id; } }}
        ondragleave={() => { if (dragOverId === folder.id) dragOverId = null; }}
        ondrop={(e) => {
          e.preventDefault();
          dragOverId = null;
          if (canDropOnFolder(folder.id)) ondropon(folder.id);
        }}
      >
        <button
          class="disclosure"
          onclick={() => ontogglefolder(folder.id)}
          aria-label={isOpen(folder.id) ? "Collapse folder" : "Expand folder"}
        >{isOpen(folder.id) ? "▾" : "▸"}</button>
        <span class="folder-icon">📁</span>
        {#if renamingFolderId === folder.id}
          <input
            class="rename-input"
            bind:value={renameDraft}
            onblur={() => commitRename(folder.id)}
            onkeydown={(e) => {
              if (e.key === "Enter") commitRename(folder.id);
              if (e.key === "Escape") oncancelrename();
            }}
          />
        {:else}
          <span class="folder-name">{folder.name}</span>
        {/if}
        <button
          class="menu-trigger"
          title="Folder actions"
          onclick={() => { menuOpenFor = menuOpenFor === folder.id ? null : folder.id; }}
        >⋯</button>
        {#if menuOpenFor === folder.id}
          <div class="folder-menu" role="menu">
            <button role="menuitem" onclick={() => { oncreatesubfolder(folder.id); menuOpenFor = null; }}>New subfolder</button>
            <button role="menuitem" onclick={() => { oncreateentryin(folder.id); menuOpenFor = null; }}>New entry here</button>
            <button role="menuitem" onclick={() => startRename(folder)}>Rename</button>
            <button
              role="menuitem"
              class="danger"
              disabled={hasChildren(folder.id)}
              title={hasChildren(folder.id) ? "Folder must be empty" : undefined}
              onclick={() => { ondeletefolder(folder.id); menuOpenFor = null; }}
            >Delete</button>
          </div>
        {/if}
      </div>
      {#if isOpen(folder.id)}
        <Self
          {folders} {entries} parentId={folder.id} depth={depth + 1}
          {selectedId} {searchQuery} {collapsedIds} {renamingFolderId} {dragging}
          {onselectentry} {ontogglefolder} {oncreatesubfolder} {oncreateentryin}
          {onstartrename} {oncommitrename} {oncancelrename} {ondeletefolder}
          {onstartdrag} {onenddrag} {ondropon}
        />
      {/if}
    </li>
  {/each}
  {#each childEntries as entry (entry.id)}
    <li>
      <div
        role="button"
        tabindex="0"
        class="tree-row entry-row"
        class:active={entry.id === selectedId}
        draggable="true"
        ondragstart={(e) => { e.dataTransfer?.setData("text/plain", ""); onstartdrag("entry", entry.id); }}
        ondragend={onenddrag}
        onclick={() => onselectentry(entry)}
        onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") onselectentry(entry); }}
      >
        <span class="entry-title">{entry.title}</span>
        <span class="entry-date">{fmtDate(entry.updatedAt)}</span>
      </div>
    </li>
  {/each}
  {#if depth === 0 && childFolders.length === 0 && childEntries.length === 0}
    <li class="list-empty">
      {searchQuery.trim() ? "No matching entries." : "No entries yet."}
    </li>
  {/if}
</ul>

{#if depth === 0 && dragging}
  <div
    class="root-dropzone"
    class:drop-target={dragOverId === "__root__"}
    ondragover={(e) => { e.preventDefault(); dragOverId = "__root__"; }}
    ondragleave={() => { if (dragOverId === "__root__") dragOverId = null; }}
    ondrop={(e) => { e.preventDefault(); dragOverId = null; ondropon(null); }}
  >⬆ Move to top level</div>
{/if}

<style>
  .kb-tree { list-style: none; margin: 0; padding: 0; }
  .kb-tree:not(.root) { padding-left: 16px; }

  .tree-row {
    display: flex; align-items: center; gap: 6px;
    padding: 6px 8px; border-radius: var(--radius-md);
    cursor: pointer; position: relative;
  }
  .tree-row:hover { background: var(--surface-hover); }
  .tree-row.drop-target { outline: 2px solid var(--accent); outline-offset: -2px; }

  .folder-row { cursor: default; }
  .disclosure {
    background: none; border: none; padding: 0; width: 14px; flex-shrink: 0;
    color: var(--text-faint); font-size: 10px; cursor: pointer;
  }
  .folder-icon { flex-shrink: 0; font-size: 13px; }
  .folder-name {
    flex: 1; min-width: 0; font-size: 13px; color: var(--text); font-weight: 500;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .rename-input {
    flex: 1; min-width: 0; font-size: 13px; font-family: var(--font-sans);
    background: var(--surface-alt); border: 1px solid var(--accent);
    border-radius: var(--radius-sm); padding: 2px 6px; color: var(--text);
  }
  .rename-input:focus { outline: none; }

  .menu-trigger {
    background: none; border: none; padding: 2px 4px; color: var(--text-faint);
    cursor: pointer; font-size: 13px; opacity: 0; flex-shrink: 0;
  }
  .tree-row:hover .menu-trigger, .menu-trigger:focus { opacity: 1; }

  .folder-menu {
    position: absolute; top: 100%; right: 0; z-index: 10;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    display: flex; flex-direction: column; min-width: 150px; padding: 4px;
  }
  .folder-menu button {
    background: none; border: none; text-align: left; padding: 6px 10px;
    font-size: 12px; color: var(--text); border-radius: var(--radius-sm); cursor: pointer;
  }
  .folder-menu button:hover:not(:disabled) { background: var(--surface-hover); }
  .folder-menu button.danger { color: var(--danger); }
  .folder-menu button:disabled { color: var(--text-faint); cursor: default; }

  .entry-row { padding: 8px 10px 8px 26px; border-left: 3px solid transparent; border-radius: var(--radius-md); }
  .entry-row.active { background: var(--surface-alt); border-left-color: var(--accent); }
  .entry-title {
    font-size: 13px; color: var(--text); font-weight: 500; flex: 1; min-width: 0;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .entry-date { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }

  .list-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 20px 0; list-style: none; }

  .root-dropzone {
    margin: 4px 8px; padding: 10px; border: 2px dashed var(--border); border-radius: var(--radius-md);
    text-align: center; font-size: 11px; color: var(--text-faint);
  }
  .root-dropzone.drop-target { border-color: var(--accent); color: var(--accent); }
</style>
