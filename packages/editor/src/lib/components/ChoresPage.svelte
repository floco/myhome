<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";
  import ChoreEditModal from "./ChoreEditModal.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
    onnewchore?: () => void;
  }

  let { store, floorStore, onnewchore }: Props = $props();

  function getRoomName(roomId: string): string {
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || `Room (${floor.name})`;
    }
    return "Unknown room";
  }

  let editChore = $state<Chore | null>(null);

  function assignmentsForChore(choreId: string) {
    return store.assignments.filter((a) => a.choreId === choreId);
  }

  function displayName(chore: Chore): string {
    let name = chore.name.trim();
    if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
    return name;
  }

  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDateTime(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await store.importFromDonetick(importToken.trim());
      importStatus = "done"; importToken = ""; showImportInput = false;
    } catch { importStatus = "error"; }
  }

  // Inline completion with notes
  type CompletingState = { kind: "chore"; id: string; notes: string } | { kind: "assignment"; id: string; notes: string };
  let completing = $state<CompletingState | null>(null);

  async function confirmComplete(): Promise<void> {
    if (!completing) return;
    const c = completing;
    completing = null;
    if (c.kind === "chore") await store.completeChore(c.id, c.notes);
    else await store.completeAssignment(c.id, c.notes);
  }

  // Per-chore history expansion
  let expandedHistory = $state<string | null>(null);
</script>

<div class="page">
  <header class="page-header">
    <h1>Chore Management</h1>
    <Button onclick={() => onnewchore?.()}>＋ New chore</Button>
    {#if !showImportInput}
      <Button variant="secondary" onclick={() => { showImportInput = true; }}>Import from Donetick</Button>
    {:else}
      <Input type="password" placeholder="API token" bind:value={importToken} />
      <Button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? "Importing…" : "Import"}
      </Button>
      <Button variant="ghost" onclick={() => { showImportInput = false; }}>Cancel</Button>
      {#if importStatus === "error"}<span class="error-msg">Failed</span>{/if}
      {#if importStatus === "done"}<span class="success-msg">{importCount} imported</span>{/if}
    {/if}
  </header>

  <div class="chore-list">
    {#each store.chores as chore (chore.id)}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <Card onclick={() => { editChore = chore; }} style="cursor:pointer">
        <div class="chore-header">
          <span class="chore-emoji">{chore.emoji}</span>
          <div class="chore-info">
            <span class="chore-name">{displayName(chore)}</span>
            <span class="chore-meta">
              {scheduleLabel(chore)}
              {#if chore.scheduleFromDue}<span class="sfd-badge" title="Schedules from due date">📅</span>{/if}
            </span>
          </div>

            {#if completing?.kind === "chore" && completing.id === chore.id}
              <input
                class="native-input note-input"
                bind:value={completing.notes}
                placeholder="Note (optional)"
                onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                onclick={(e) => { e.stopPropagation(); }}
              />
              <button class="icon-btn confirm-btn" onclick={(e) => { e.stopPropagation(); confirmComplete(); }}>✓</button>
              <button class="icon-btn" onclick={(e) => { e.stopPropagation(); completing = null; }}>✕</button>
            {:else}
              <button class="icon-btn" title="Mark all done" onclick={(e) => { e.stopPropagation(); completing = { kind: "chore", id: chore.id, notes: "" }; }}>✓ All done</button>
            {/if}

            <button class="icon-btn" onclick={(e) => { e.stopPropagation(); editChore = chore; }}>✏️</button>
            <button
              class="icon-btn"
              title={expandedHistory === chore.id ? "Hide history" : "Show history"}
              class:active-hist={expandedHistory === chore.id}
              onclick={(e) => { e.stopPropagation(); expandedHistory = expandedHistory === chore.id ? null : chore.id; }}
            >🕐</button>
          </div>

          {@const instances = assignmentsForChore(chore.id)}
          {#if instances.length > 0}
            <div class="instances">
              {#each instances as a (a.id)}
                <div class="instance-row">
                  <span class="instance-where">
                    {a.roomId ? getRoomName(a.roomId) : "🏠 Whole house"}
                  </span>
                  <span class="instance-due">Due: {formatDate(a.nextDueDate)}</span>
                  {#if completing?.kind === "assignment" && completing.id === a.id}
                    <input
                      class="native-input note-input-sm"
                      bind:value={completing.notes}
                      placeholder="Note (optional)"
                      onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                    />
                    <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
                    <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
                  {:else}
                    <button class="icon-btn" onclick={() => { completing = { kind: "assignment", id: a.id, notes: "" }; }}>✓</button>
                  {/if}
                  <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
                </div>
              {/each}
            </div>
          {:else}
            <div class="no-instances">Not assigned to any room</div>
          {/if}

          {#if expandedHistory === chore.id}
            {@const history = store.getCompletionsForChore(chore.id).slice().reverse()}
            <div class="history-section">
              <div class="history-title">Completion history</div>
              {#if history.length === 0}
                <div class="no-history">No completions yet</div>
              {:else}
                {#each history as rec (rec.id)}
                  <div class="history-row">
                    <span class="hist-date">{formatDateTime(rec.completedAt)}</span>
                    {#if rec.scheduledDue}<span class="hist-due">was due {formatDate(rec.scheduledDue)}</span>{/if}
                    {#if rec.notes}<span class="hist-notes">{rec.notes}</span>{/if}
                  </div>
                {/each}
              {/if}
            </div>
          {/if}
      </Card>
    {/each}

    {#if store.chores.length === 0}
      <div class="empty-state">
        No chores yet. Click <strong>＋ New chore</strong> to get started.
      </div>
    {/if}
  </div>
</div>

<ChoreEditModal chore={editChore} {store} onclose={() => { editChore = null; }} />

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); color: var(--text); font-family: var(--font-sans); }

  .page-header {
    display: flex; align-items: center; gap: 8px 12px; flex-wrap: wrap;
    padding: var(--space-2) var(--space-4); background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .page-header h1 { font-size: 16px; margin: 0; flex: 1; min-width: 120px; color: var(--text); }
  .page-header :global(.ui-input) { flex: 0 1 220px; }

  .chore-list { flex: 1; overflow-y: auto; padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-3); }

  .chore-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
  .chore-emoji { font-size: 18px; flex-shrink: 0; }
  .chore-info { flex: 1; min-width: 80px; display: flex; flex-direction: column; gap: 2px; }
  .chore-name { font-weight: 600; color: var(--text); word-break: break-word; }
  .chore-meta { font-size: 11px; color: var(--text-faint); display: flex; align-items: center; gap: 4px; }
  .sfd-badge { font-size: 11px; cursor: help; }

  .native-input {
    padding: 6px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 12px;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .note-input { flex: 1; min-width: 100px; }
  .note-input-sm { width: 110px; font-size: 11px; }
  .emoji-field { width: 60px; }

  .icon-btn {
    padding: 6px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px;
    min-height: 34px; touch-action: manipulation;
  }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .icon-btn.danger:hover { color: var(--danger); }
  .confirm-btn { background: var(--success) !important; color: var(--accent-contrast) !important; }
  .confirm-btn:hover { opacity: 0.85; }
  .active-hist { background: var(--surface-hover) !important; color: var(--accent) !important; }

  .instances { display: flex; flex-direction: column; gap: 6px; padding-left: 12px; border-left: 2px solid var(--border); margin-top: 4px; }
  .instance-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; }
  .instance-where { flex: 1; min-width: 80px; color: var(--text-muted); }
  .instance-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .no-instances { font-size: 11px; color: var(--text-faint); padding-left: 12px; font-style: italic; margin-top: 4px; }

  .history-section {
    margin-top: 8px; padding: var(--space-2) var(--space-3);
    background: var(--surface-alt); border-radius: var(--radius-sm); border: 1px solid var(--border);
  }
  .history-title { font-size: 10px; text-transform: uppercase; color: var(--text-faint); letter-spacing: 0.06em; margin-bottom: 6px; }
  .no-history { font-size: 11px; color: var(--text-faint); font-style: italic; }
  .history-row { display: flex; align-items: baseline; gap: 10px; padding: 3px 0; font-size: 11px; flex-wrap: wrap; }
  .hist-date { color: var(--text-muted); white-space: nowrap; flex-shrink: 0; }
  .hist-due { color: var(--text-faint); white-space: nowrap; }
  .hist-notes { color: var(--text-muted); font-style: italic; }


  .error-msg { color: var(--danger); font-size: 11px; }
  .success-msg { color: var(--success); font-size: 11px; }

  .empty-state { padding: 40px 20px; text-align: center; color: var(--text-faint); font-size: 13px; line-height: 1.6; }

  @media (max-width: 500px) {
    .page-header { padding: 8px 10px; }
    .chore-list { padding: 8px; gap: 8px; }
    .chore-header { gap: 6px; }
    .edit-form input[type="number"] { width: 100%; }
    .row-btns { flex-direction: column; }
    .row-btns :global(.ui-button) { width: 100%; }
    .instance-row { gap: 6px; }
  }
</style>
