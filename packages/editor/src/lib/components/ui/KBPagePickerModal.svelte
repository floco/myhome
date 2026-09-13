<!-- packages/editor/src/lib/components/ui/KBPagePickerModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { KBEntry } from "../../kbStore.svelte";
  import Modal from "./Modal.svelte";
  import Input from "./Input.svelte";
  import { kbPagePath } from "./kbPagePath";

  interface Props {
    open: boolean;
    entries: KBEntry[];
    onselect: (entry: KBEntry) => void;
    onclose: () => void;
  }

  let { open, entries, onselect, onclose }: Props = $props();

  let searchQuery = $state("");

  $effect(() => {
    if (open) searchQuery = "";
  });

  const candidates = $derived.by(() => {
    const q = searchQuery.trim().toLowerCase();
    return entries
      .filter((e) => !q || e.title.toLowerCase().includes(q))
      .map((e) => ({ entry: e, path: kbPagePath(entries, e) }))
      .sort((a, b) => a.path.localeCompare(b.path));
  });
</script>

<Modal {open} title={$_('kb.page.pageLinkModalTitle')} {onclose} width="420px">
  <div class="picker-modal">
    <Input placeholder={$_('kb.page.pageLinkSearchPlaceholder')} bind:value={searchQuery} />
    <ul class="picker-list">
      {#each candidates as { entry, path } (entry.id)}
        <li>
          <button type="button" class="picker-item" onclick={() => onselect(entry)}>
            <span class="picker-icon">{entry.icon || "📄"}</span>
            <span class="picker-path">{path}</span>
          </button>
        </li>
      {/each}
      {#if candidates.length === 0}
        <li class="picker-empty">{$_('kb.page.pageLinkNoPages')}</li>
      {/if}
    </ul>
  </div>
</Modal>

<style>
  .picker-modal { display: flex; flex-direction: column; gap: var(--space-3); }
  .picker-list {
    list-style: none; margin: 0; padding: 0;
    max-height: 320px; overflow-y: auto;
    display: flex; flex-direction: column; gap: 2px;
  }
  .picker-item {
    display: flex; align-items: center; gap: 8px; width: 100%;
    background: none; border: none; text-align: left; cursor: pointer;
    padding: 8px 10px; border-radius: var(--radius-sm); color: var(--text); font-size: 13px;
  }
  .picker-item:hover { background: var(--surface-hover); }
  .picker-icon { flex-shrink: 0; font-size: 13px; }
  .picker-path { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .picker-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 16px 0; }
</style>
