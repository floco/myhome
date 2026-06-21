<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";
  import DatePicker from "./DatePicker.svelte";

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

  let editingId = $state<string | null>(null);
  let editName = $state("");
  let editEmoji = $state("");
  let editPeriodDays = $state(30);
  let editNextDue = $state("");
  let editScheduleFromDue = $state(false);

  function startEdit(chore: Chore): void {
    editingId = chore.id;
    editName = chore.name;
    editEmoji = chore.emoji;
    editPeriodDays = chore.periodDays;
    editNextDue = chore.nextDueDate.slice(0, 10);
    editScheduleFromDue = chore.scheduleFromDue;
  }

  async function handleUpdate(): Promise<void> {
    if (!editingId) return;
    await store.updateChore(editingId, {
      name: editName.trim(),
      emoji: editEmoji.trim() || "📋",
      periodDays: editPeriodDays,
      nextDueDate: new Date(editNextDue).toISOString(),
      scheduleFromDue: editScheduleFromDue,
    });
    editingId = null;
  }

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
    <button class="add-btn-header" onclick={() => onnewchore?.()}>＋ New chore</button>
    {#if !showImportInput}
      <button onclick={() => { showImportInput = true; }}>Import from Donetick</button>
    {:else}
      <input type="password" placeholder="API token" bind:value={importToken} class="token-input"/>
      <button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? "Importing…" : "Import"}
      </button>
      <button onclick={() => { showImportInput = false; }}>Cancel</button>
      {#if importStatus === "error"}<span class="error-msg">Failed</span>{/if}
      {#if importStatus === "done"}<span class="success-msg">{importCount} imported</span>{/if}
    {/if}
  </header>

  <div class="chore-list">
    {#each store.chores as chore (chore.id)}
      <div class="chore-card">
        {#if editingId === chore.id}
          <div class="edit-form">
            <input bind:value={editName} placeholder="Name"/>
            <input bind:value={editEmoji} placeholder="Emoji" maxlength="4" style="width:60px"/>
            <label>Period (days) <input type="number" bind:value={editPeriodDays} min="1"/></label>
            <label>Default due <DatePicker bind:value={editNextDue} /></label>
            <div class="sfd-row">
              <input type="checkbox" id="sfd-{chore.id}" bind:checked={editScheduleFromDue}/>
              <label for="sfd-{chore.id}" title="Next due = planned date + period">Schedule from due date</label>
            </div>
            <div class="row-btns">
              <button class="primary-btn" onclick={handleUpdate}>Save</button>
              <button onclick={() => { editingId = null; }}>Cancel</button>
            </div>
          </div>
        {:else}
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
                class="note-input"
                bind:value={completing.notes}
                placeholder="Note (optional)"
                onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
              />
              <button class="confirm-btn" onclick={confirmComplete}>✓</button>
              <button onclick={() => { completing = null; }}>✕</button>
            {:else}
              <button title="Mark all done" onclick={() => { completing = { kind: "chore", id: chore.id, notes: "" }; }}>✓ All done</button>
            {/if}

            <button onclick={() => startEdit(chore)}>✏️</button>
            <button
              title={expandedHistory === chore.id ? "Hide history" : "Show history"}
              class:active-hist={expandedHistory === chore.id}
              onclick={() => { expandedHistory = expandedHistory === chore.id ? null : chore.id; }}
            >🕐</button>
            <button onclick={() => store.deleteChore(chore.id)}>🗑️</button>
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
                      class="note-input-sm"
                      bind:value={completing.notes}
                      placeholder="Note (optional)"
                      onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                    />
                    <button class="confirm-btn" onclick={confirmComplete}>✓</button>
                    <button onclick={() => { completing = null; }}>✕</button>
                  {:else}
                    <button onclick={() => { completing = { kind: "assignment", id: a.id, notes: "" }; }}>✓</button>
                  {/if}
                  <button onclick={() => store.deleteAssignment(a.id)}>✕</button>
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
        {/if}
      </div>
    {/each}

    {#if store.chores.length === 0}
      <div class="empty-state">
        No chores yet. Click <strong>＋ New chore</strong> to get started.
      </div>
    {/if}
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: #1a1a2e; color: #ccc; font-family: sans-serif; }

  .page-header {
    display: flex; align-items: center; gap: 8px 12px; flex-wrap: wrap;
    padding: 8px 16px; background: #252535; border-bottom: 1px solid #333; flex-shrink: 0;
  }
  .page-header h1 { font-size: 16px; margin: 0; flex: 1; min-width: 120px; }

  .add-btn-header {
    padding: 6px 12px; border: none; border-radius: 4px;
    background: #2a6; color: #fff; cursor: pointer; font-size: 12px; font-weight: 600;
    min-height: 34px; white-space: nowrap;
  }
  .add-btn-header:hover { background: #3b7; }

  .chore-list { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 12px; }

  .chore-card { background: #252535; border: 1px solid #333; border-radius: 6px; padding: 12px; }

  .chore-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
  .chore-emoji { font-size: 18px; flex-shrink: 0; }
  .chore-info { flex: 1; min-width: 80px; display: flex; flex-direction: column; gap: 2px; }
  .chore-name { font-weight: 600; color: #eee; word-break: break-word; }
  .chore-meta { font-size: 11px; color: #666; display: flex; align-items: center; gap: 4px; }
  .sfd-badge { font-size: 11px; cursor: help; }

  .note-input { flex: 1; min-width: 100px; padding: 4px 8px; background: #2a2a3a; border: 1px solid #555; border-radius: 3px; color: #ccc; font-size: 12px; }
  .note-input-sm { width: 110px; padding: 3px 6px; background: #2a2a3a; border: 1px solid #555; border-radius: 3px; color: #ccc; font-size: 11px; }
  .confirm-btn { background: #2a6 !important; color: #fff !important; }
  .confirm-btn:hover { background: #3b7 !important; }

  .instances { display: flex; flex-direction: column; gap: 6px; padding-left: 12px; border-left: 2px solid #333; }
  .instance-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; }
  .instance-where { flex: 1; min-width: 80px; color: #aaa; }
  .instance-due { color: #666; font-size: 11px; white-space: nowrap; }
  .no-instances { font-size: 11px; color: #555; padding-left: 12px; font-style: italic; }

  .history-section {
    margin-top: 8px; padding: 8px 12px;
    background: #1a1a2e; border-radius: 4px; border: 1px solid #2a2a3a;
  }
  .history-title { font-size: 10px; text-transform: uppercase; color: #666; letter-spacing: 0.06em; margin-bottom: 6px; }
  .no-history { font-size: 11px; color: #555; font-style: italic; }
  .history-row { display: flex; align-items: baseline; gap: 10px; padding: 3px 0; font-size: 11px; flex-wrap: wrap; }
  .hist-date { color: #888; white-space: nowrap; flex-shrink: 0; }
  .hist-due { color: #555; white-space: nowrap; }
  .hist-notes { color: #aaa; font-style: italic; }
  .active-hist { background: #2a2a4a !important; }

  .sfd-row { display: flex; align-items: center; gap: 6px; font-size: 12px; }
  .sfd-row input[type="checkbox"] { width: auto; }
  .sfd-row label { color: #aaa; cursor: pointer; }

  button {
    padding: 6px 10px; border: none; border-radius: 4px;
    background: #3a3a5a; color: #ccc; cursor: pointer; font-size: 12px;
    min-height: 34px; touch-action: manipulation;
  }
  button:hover { background: #4a4a6a; }
  button:disabled { opacity: 0.5; cursor: default; }
  .primary-btn { background: #2a6; color: #fff; }
  .primary-btn:hover { background: #3b7; }

  .edit-form { display: flex; flex-direction: column; gap: 6px; }
  input {
    padding: 6px 8px; border: 1px solid #444; border-radius: 3px;
    background: #2a2a3a; color: #ccc; font-size: 13px;
    width: 100%; box-sizing: border-box;
  }
  input[type="number"] { width: 100px; }
  input[type="checkbox"] { width: auto; }
  label { display: flex; flex-direction: column; gap: 2px; font-size: 11px; color: #888; }
  .row-btns { display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap; }

  .token-input { width: 100%; max-width: 260px; }
  .error-msg { color: #f44336; font-size: 11px; }
  .success-msg { color: #4caf50; font-size: 11px; }

  .empty-state { padding: 40px 20px; text-align: center; color: #555; font-size: 13px; line-height: 1.6; }

  @media (max-width: 500px) {
    .page-header { padding: 8px 10px; }
    .chore-list { padding: 8px; gap: 8px; }
    .chore-card { padding: 10px; }
    .chore-header { gap: 6px; }
    input[type="number"] { width: 100%; }
    .row-btns { flex-direction: column; }
    .row-btns button { width: 100%; }
    .instance-row { gap: 6px; }
  }
</style>
