<!-- packages/editor/src/lib/components/ui/KBTrash.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { KBEntry } from "../../kbStore.svelte";
  import Button from "./Button.svelte";
  import Modal from "./Modal.svelte";

  interface Props {
    entries: KBEntry[];
    onrestore: (id: string) => void;
    ondeleteforever: (id: string) => void;
    onemptytrash: () => void;
  }
  let { entries, onrestore, ondeleteforever, onemptytrash }: Props = $props();

  let confirmEmptyAll = $state(false);
  let confirmDeleteId = $state<string | null>(null);
  const confirmDeleteEntry = $derived(
    confirmDeleteId ? (entries.find((e) => e.id === confirmDeleteId) ?? null) : null,
  );

  function fmtDate(iso: string | null | undefined): string {
    return iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  }

  function handleConfirmEmpty(): void {
    onemptytrash();
    confirmEmptyAll = false;
  }

  function handleConfirmDeleteForever(): void {
    if (confirmDeleteId) ondeleteforever(confirmDeleteId);
    confirmDeleteId = null;
  }
</script>

<div class="kb-trash">
  <div class="trash-header">
    <h2>{$_('kb.trash.title')}</h2>
    {#if entries.length > 0}
      <Button variant="secondary" onclick={() => { confirmEmptyAll = true; }}>{$_('kb.trash.emptyTrash')}</Button>
    {/if}
  </div>
  {#if entries.length === 0}
    <div class="trash-empty">{$_('kb.trash.trashIsEmpty')}</div>
  {:else}
    <ul class="trash-list">
      {#each entries as entry (entry.id)}
        <li class="trash-row">
          <span class="trash-icon">{entry.icon || "📄"}</span>
          <span class="trash-title">{entry.title}</span>
          <span class="trash-date">{$_('kb.trash.deletedOn', { values: { date: fmtDate(entry.deletedAt) } })}</span>
          <div class="trash-actions">
            <Button variant="secondary" onclick={() => onrestore(entry.id)}>{$_('kb.trash.restore')}</Button>
            <Button variant="ghost" onclick={() => { confirmDeleteId = entry.id; }} title={$_('kb.trash.deleteForeverTitle')}>🗑</Button>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<Modal open={confirmEmptyAll} title={$_('kb.trash.emptyTrash')} onclose={() => { confirmEmptyAll = false; }} width="420px">
  <p>{$_('kb.trash.confirmEmptyBody', { values: { n: entries.length } })}</p>
  {#snippet footer()}
    <Button variant="ghost" onclick={() => { confirmEmptyAll = false; }}>{$_('common.cancel')}</Button>
    <Button variant="danger" onclick={handleConfirmEmpty}>{$_('kb.trash.emptyTrash')}</Button>
  {/snippet}
</Modal>

<Modal open={confirmDeleteId !== null} title={$_('kb.trash.deleteForeverTitle')} onclose={() => { confirmDeleteId = null; }} width="420px">
  <p>{$_('kb.trash.confirmDeletePrefix')} <strong>{confirmDeleteEntry?.title}</strong>{$_('kb.trash.confirmDeleteSuffix')}</p>
  {#snippet footer()}
    <Button variant="ghost" onclick={() => { confirmDeleteId = null; }}>{$_('common.cancel')}</Button>
    <Button variant="danger" onclick={handleConfirmDeleteForever}>{$_('kb.trash.deleteForeverButton')}</Button>
  {/snippet}
</Modal>

<style>
  .kb-trash { padding: var(--space-4); flex: 1; overflow-y: auto; }
  .trash-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
  .trash-header h2 { font-size: 16px; font-weight: 600; color: var(--text); margin: 0; flex: 1; }
  .trash-empty { color: var(--text-faint); font-size: 13px; }
  .trash-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .trash-row {
    display: flex; align-items: center; gap: 8px; padding: 8px 10px;
    border: 1px solid var(--border); border-radius: var(--radius-md);
  }
  .trash-icon { font-size: 14px; flex-shrink: 0; }
  .trash-title { flex: 1; min-width: 0; font-size: 13px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .trash-date { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
  .trash-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
</style>
