<!-- packages/editor/src/lib/components/ui/KBTrash.svelte -->
<script lang="ts">
  import type { KBEntry } from "../../kbStore.svelte";
  import Button from "./Button.svelte";

  interface Props {
    entries: KBEntry[];
    onrestore: (id: string) => void;
    ondeleteforever: (id: string) => void;
    onemptytrash: () => void;
  }
  let { entries, onrestore, ondeleteforever, onemptytrash }: Props = $props();

  let confirmEmptyAll = $state(false);
  let confirmDeleteId = $state<string | null>(null);

  function fmtDate(iso: string | null | undefined): string {
    return iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  }
</script>

<div class="kb-trash">
  <div class="trash-header">
    <h2>Trash</h2>
    {#if entries.length > 0}
      {#if confirmEmptyAll}
        <span class="confirm-text">Permanently delete all {entries.length} pages?</span>
        <Button variant="danger" onclick={() => { onemptytrash(); confirmEmptyAll = false; }}>✓</Button>
        <Button variant="ghost" onclick={() => { confirmEmptyAll = false; }}>✕</Button>
      {:else}
        <Button variant="secondary" onclick={() => { confirmEmptyAll = true; }}>Empty Trash</Button>
      {/if}
    {/if}
  </div>
  {#if entries.length === 0}
    <div class="trash-empty">Trash is empty.</div>
  {:else}
    <ul class="trash-list">
      {#each entries as entry (entry.id)}
        <li class="trash-row">
          <span class="trash-icon">{entry.icon || "📄"}</span>
          <span class="trash-title">{entry.title}</span>
          <span class="trash-date">Deleted {fmtDate(entry.deletedAt)}</span>
          <div class="trash-actions">
            <Button variant="secondary" onclick={() => onrestore(entry.id)}>Restore</Button>
            {#if confirmDeleteId === entry.id}
              <Button variant="danger" onclick={() => { ondeleteforever(entry.id); confirmDeleteId = null; }}>✓</Button>
              <Button variant="ghost" onclick={() => { confirmDeleteId = null; }}>✕</Button>
            {:else}
              <Button variant="ghost" onclick={() => { confirmDeleteId = entry.id; }} title="Delete forever">🗑</Button>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .kb-trash { padding: var(--space-4); flex: 1; overflow-y: auto; }
  .trash-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
  .trash-header h2 { font-size: 16px; font-weight: 600; color: var(--text); margin: 0; flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
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
