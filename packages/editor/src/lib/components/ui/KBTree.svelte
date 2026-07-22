<!-- packages/editor/src/lib/components/ui/KBTree.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { KBEntry } from "../../kbStore.svelte";
  import Self from "./KBTree.svelte";

  interface DropIndicator {
    id: string;
    position: "before" | "after" | "inside";
  }

  interface Props {
    entries: KBEntry[];
    parentId?: string | null;
    depth?: number;
    selectedId: string | null;
    searchQuery: string;
    collapsedIds: Set<string>;
    renamingId: string | null;
    dragging: string | null;
    onselect: (entry: KBEntry) => void;
    ontoggle: (id: string) => void;
    oncreatechild: (parentId: string) => void;
    onstartrename: (id: string) => void;
    oncommitrename: (id: string, title: string) => void;
    oncancelrename: () => void;
    ondelete: (id: string) => void;
    onstartdrag: (id: string) => void;
    onenddrag: () => void;
    ondrop: (draggedId: string, targetParentId: string | null, orderedIds: string[] | null) => void;
  }

  let {
    entries, parentId = null, depth = 0, selectedId, searchQuery, collapsedIds,
    renamingId, dragging,
    onselect, ontoggle, oncreatechild, onstartrename, oncommitrename, oncancelrename, ondelete,
    onstartdrag, onenddrag, ondrop,
  }: Props = $props();

  let renameDraft = $state("");
  let menuOpenFor = $state<string | null>(null);
  let dropIndicator = $state<DropIndicator | null>(null);

  function matches(text: string): boolean {
    const q = searchQuery.trim().toLowerCase();
    return !q || text.toLowerCase().includes(q);
  }

  // A live page whose parentId doesn't match any other live page (null, or
  // pointing at a page that's been trashed/deleted) renders as top-level.
  function isRootLevel(entry: KBEntry): boolean {
    return entry.parentId === null || !entries.some((p) => p.id === entry.parentId);
  }

  const visibleIds = $derived.by(() => {
    const q = searchQuery.trim();
    if (!q) return null;
    const childrenOf = new Map<string | null, KBEntry[]>();
    for (const e of entries) {
      const key = isRootLevel(e) ? null : e.parentId;
      const list = childrenOf.get(key) ?? [];
      list.push(e);
      childrenOf.set(key, list);
    }
    const visible = new Set<string>();
    function visit(entry: KBEntry): boolean {
      const ownMatch = matches(entry.title);
      const hasMatchingChild = (childrenOf.get(entry.id) ?? []).map(visit).some(Boolean);
      const keep = ownMatch || hasMatchingChild;
      if (keep) visible.add(entry.id);
      return keep;
    }
    for (const e of childrenOf.get(null) ?? []) visit(e);
    return visible;
  });

  const childEntries = $derived(
    entries
      .filter((e) => (parentId === null ? isRootLevel(e) : e.parentId === parentId))
      .filter((e) => visibleIds === null || visibleIds.has(e.id))
      .slice()
      .sort((a, b) => a.order - b.order),
  );

  function isOpen(id: string): boolean {
    return searchQuery.trim() !== "" || !collapsedIds.has(id);
  }

  function hasChildren(id: string): boolean {
    return entries.some((e) => e.parentId === id);
  }

  function startRename(entry: KBEntry): void {
    renameDraft = entry.title;
    menuOpenFor = null;
    onstartrename(entry.id);
  }

  function commitRename(id: string): void {
    const title = renameDraft.trim();
    if (title) oncommitrename(id, title);
    else oncancelrename();
  }

  // Any click that reaches window without having been stopped by a handler
  // inside the menu or its trigger (both call stopPropagation) is "outside".
  function handleWindowClick(): void {
    menuOpenFor = null;
  }

  function wouldCreateCycle(draggedId: string, targetId: string): boolean {
    if (draggedId === targetId) return true;
    let current: string | null = targetId;
    const seen = new Set<string>();
    while (current !== null) {
      if (current === draggedId) return true;
      if (seen.has(current)) return false;
      seen.add(current);
      const e = entries.find((x) => x.id === current);
      current = e ? e.parentId : null;
    }
    return false;
  }

  function handleDragOver(e: DragEvent, entry: KBEntry): void {
    if (!dragging || dragging === entry.id || wouldCreateCycle(dragging, entry.id)) return;
    e.preventDefault();
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const ratio = (e.clientY - rect.top) / rect.height;
    const position = ratio < 0.25 ? "before" : ratio > 0.75 ? "after" : "inside";
    dropIndicator = { id: entry.id, position };
  }

  function handleDrop(e: DragEvent, entry: KBEntry): void {
    e.preventDefault();
    const indicator = dropIndicator;
    dropIndicator = null;
    if (!dragging || dragging === entry.id || wouldCreateCycle(dragging, entry.id) || !indicator) return;
    if (indicator.position === "inside") {
      ondrop(dragging, entry.id, null);
      return;
    }
    const siblings = entries
      .filter((s) => s.parentId === entry.parentId && s.id !== dragging)
      .sort((a, b) => a.order - b.order);
    const targetIndex = siblings.findIndex((s) => s.id === entry.id);
    const insertAt = indicator.position === "before" ? targetIndex : targetIndex + 1;
    const orderedIds = siblings.map((s) => s.id);
    orderedIds.splice(insertAt, 0, dragging);
    ondrop(dragging, entry.parentId, orderedIds);
  }
</script>

<svelte:window onclick={handleWindowClick} />

<ul class="kb-tree" class:root={depth === 0}>
  {#each childEntries as entry (entry.id)}
    <li>
      <div
        role="button"
        tabindex="0"
        class="tree-row"
        class:active={entry.id === selectedId}
        class:drop-before={dropIndicator?.id === entry.id && dropIndicator.position === "before"}
        class:drop-after={dropIndicator?.id === entry.id && dropIndicator.position === "after"}
        class:drop-inside={dropIndicator?.id === entry.id && dropIndicator.position === "inside"}
        draggable="true"
        ondragstart={(e) => { e.dataTransfer?.setData("text/plain", ""); onstartdrag(entry.id); }}
        ondragend={() => { dropIndicator = null; onenddrag(); }}
        ondragover={(e) => handleDragOver(e, entry)}
        ondragleave={() => { if (dropIndicator?.id === entry.id) dropIndicator = null; }}
        ondrop={(e) => handleDrop(e, entry)}
        onclick={() => onselect(entry)}
        onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") onselect(entry); }}
      >
        {#if hasChildren(entry.id)}
          <button
            class="disclosure"
            onclick={(e) => { e.stopPropagation(); ontoggle(entry.id); }}
            aria-label={isOpen(entry.id) ? $_('kb.tree.collapse') : $_('kb.tree.expand')}
          >{isOpen(entry.id) ? "▼" : "▶"}</button>
        {:else}
          <span class="disclosure-spacer"></span>
        {/if}
        <span class="page-icon">{entry.icon || "📄"}</span>
        {#if renamingId === entry.id}
          <input
            class="rename-input"
            bind:value={renameDraft}
            onclick={(e) => e.stopPropagation()}
            onblur={() => commitRename(entry.id)}
            onkeydown={(e) => {
              if (e.key === "Enter") commitRename(entry.id);
              if (e.key === "Escape") oncancelrename();
            }}
          />
        {:else}
          <span class="page-title">{entry.title}</span>
        {/if}
        <button
          class="menu-trigger"
          title={$_('kb.tree.pageActions')}
          onclick={(e) => { e.stopPropagation(); menuOpenFor = menuOpenFor === entry.id ? null : entry.id; }}
        >⋯</button>
        {#if menuOpenFor === entry.id}
          <div class="page-menu" role="menu" onclick={(e) => e.stopPropagation()}>
            <button role="menuitem" onclick={(e) => { e.stopPropagation(); oncreatechild(entry.id); menuOpenFor = null; }}>{$_('kb.tree.addChildPage')}</button>
            <button role="menuitem" onclick={(e) => { e.stopPropagation(); startRename(entry); }}>{$_('kb.tree.rename')}</button>
            <button role="menuitem" class="danger" onclick={(e) => { e.stopPropagation(); ondelete(entry.id); menuOpenFor = null; }}>{$_('common.delete')}</button>
          </div>
        {/if}
      </div>
      {#if hasChildren(entry.id) && isOpen(entry.id)}
        <Self
          {entries} parentId={entry.id} depth={depth + 1}
          {selectedId} {searchQuery} {collapsedIds} {renamingId} {dragging}
          {onselect} {ontoggle} {oncreatechild} {onstartrename} {oncommitrename} {oncancelrename} {ondelete}
          {onstartdrag} {onenddrag} {ondrop}
        />
      {/if}
    </li>
  {/each}
  {#if depth === 0 && childEntries.length === 0}
    <li class="list-empty">
      {searchQuery.trim() ? $_('kb.tree.noMatchingPages') : $_('kb.tree.noPagesYet')}
    </li>
  {/if}
</ul>

<style>
  .kb-tree { list-style: none; margin: 0; padding: 0; }
  .kb-tree:not(.root) { padding-left: 16px; }

  .tree-row {
    display: flex; align-items: center; gap: 6px;
    padding: 6px 8px; border-radius: var(--radius-md);
    cursor: pointer; position: relative;
    border-left: 3px solid transparent;
  }
  .tree-row:hover { background: var(--surface-hover); }
  .tree-row.active { background: color-mix(in srgb, var(--accent) 10%, transparent); }
  .tree-row.active .page-title { font-weight: 700; }

  /* Nest target ("will be included in this page"): a filled highlight on the
     row itself. Reorder target ("will be inserted between rows"): an actual
     line spanning the row's top/bottom edge -- deliberately a different
     visual language so the two drop outcomes can't be confused mid-drag. */
  .tree-row.drop-inside {
    background: color-mix(in srgb, var(--accent) 15%, transparent);
    outline: 1px solid var(--accent); outline-offset: -1px;
  }
  .tree-row.drop-before::before,
  .tree-row.drop-after::after {
    content: ""; position: absolute; left: 2px; right: 2px; height: 2px;
    background: var(--accent); border-radius: 1px; pointer-events: none;
  }
  .tree-row.drop-before::before { top: -1px; }
  .tree-row.drop-after::after { bottom: -1px; }

  .disclosure {
    display: flex; align-items: center; justify-content: center;
    background: none; border: none; padding: 0; width: 18px; height: 18px; flex-shrink: 0;
    color: var(--text); font-size: 13px; line-height: 1; cursor: pointer; border-radius: var(--radius-sm);
  }
  .disclosure:hover { background: var(--surface-hover); }
  .disclosure-spacer { width: 18px; flex-shrink: 0; }
  .page-icon { flex-shrink: 0; font-size: 13px; }
  .page-title {
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

  .page-menu {
    position: absolute; top: 100%; right: 0; z-index: 10;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    display: flex; flex-direction: column; min-width: 150px; padding: 4px;
  }
  .page-menu button {
    background: none; border: none; text-align: left; padding: 6px 10px;
    font-size: 12px; color: var(--text); border-radius: var(--radius-sm); cursor: pointer;
  }
  .page-menu button:hover { background: var(--surface-hover); }
  .page-menu button.danger { color: var(--danger); }

  .list-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 20px 0; list-style: none; }
</style>
