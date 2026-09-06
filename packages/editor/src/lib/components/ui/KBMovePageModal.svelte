<!-- packages/editor/src/lib/components/ui/KBMovePageModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { KBEntry } from "../../kbStore.svelte";
  import Modal from "./Modal.svelte";
  import Input from "./Input.svelte";

  interface Props {
    open: boolean;
    entries: KBEntry[];
    pageId: string;
    onmove: (targetParentId: string | null) => void;
    onclose: () => void;
  }

  let { open, entries, pageId, onmove, onclose }: Props = $props();

  let searchQuery = $state("");

  $effect(() => {
    if (open) searchQuery = "";
  });

  const currentParentId = $derived(entries.find((e) => e.id === pageId)?.parentId ?? null);

  // Excludes the page itself and its entire subtree -- moving a page into
  // one of its own descendants would create a cycle.
  const excludedIds = $derived.by(() => {
    const excluded = new Set<string>([pageId]);
    let added = true;
    while (added) {
      added = false;
      for (const e of entries) {
        if (e.parentId && excluded.has(e.parentId) && !excluded.has(e.id)) {
          excluded.add(e.id);
          added = true;
        }
      }
    }
    return excluded;
  });

  function pathFor(entry: KBEntry): string {
    const parts: string[] = [entry.title];
    let current = entry.parentId;
    const seen = new Set<string>();
    while (current && !seen.has(current)) {
      seen.add(current);
      const parent = entries.find((e) => e.id === current);
      if (!parent) break;
      parts.unshift(parent.title);
      current = parent.parentId;
    }
    return parts.join(" › ");
  }

  const candidates = $derived.by(() => {
    const q = searchQuery.trim().toLowerCase();
    return entries
      .filter((e) => !excludedIds.has(e.id) && e.id !== currentParentId)
      .filter((e) => !q || e.title.toLowerCase().includes(q))
      .map((e) => ({ entry: e, path: pathFor(e) }))
      .sort((a, b) => a.path.localeCompare(b.path));
  });

  const showTopLevel = $derived(currentParentId !== null && !searchQuery.trim());
</script>

<Modal {open} title={$_('kb.page.moveModalTitle')} {onclose} width="420px">
  <div class="move-modal">
    <Input placeholder={$_('kb.page.moveSearchPlaceholder')} bind:value={searchQuery} />
    <ul class="move-list">
      {#if showTopLevel}
        <li>
          <button type="button" class="move-item" onclick={() => onmove(null)}>
            <span class="move-icon">📁</span>
            <span class="move-title">{$_('kb.page.moveTopLevel')}</span>
          </button>
        </li>
      {/if}
      {#each candidates as { entry, path } (entry.id)}
        <li>
          <button type="button" class="move-item" onclick={() => onmove(entry.id)}>
            <span class="move-icon">{entry.icon || "📄"}</span>
            <span class="move-path">{path}</span>
          </button>
        </li>
      {/each}
      {#if !showTopLevel && candidates.length === 0}
        <li class="move-empty">{$_('kb.page.moveNoCandidates')}</li>
      {/if}
    </ul>
  </div>
</Modal>

<style>
  .move-modal { display: flex; flex-direction: column; gap: var(--space-3); }
  .move-list {
    list-style: none; margin: 0; padding: 0;
    max-height: 320px; overflow-y: auto;
    display: flex; flex-direction: column; gap: 2px;
  }
  .move-item {
    display: flex; align-items: center; gap: 8px; width: 100%;
    background: none; border: none; text-align: left; cursor: pointer;
    padding: 8px 10px; border-radius: var(--radius-sm); color: var(--text); font-size: 13px;
  }
  .move-item:hover { background: var(--surface-hover); }
  .move-icon { flex-shrink: 0; font-size: 13px; }
  .move-title { font-weight: 500; }
  .move-path { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .move-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 16px 0; }
</style>
