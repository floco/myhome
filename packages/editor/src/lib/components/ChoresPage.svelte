<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import ChoreEditModal from "./ChoreEditModal.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;
  type Assignment = ChoreStore["assignments"][number];

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
    onnewchore?: () => void;
  }

  let { store, floorStore, onnewchore }: Props = $props();

  let editChore = $state<Chore | null>(null);
  let searchQuery = $state("");
  let expandedHistory = $state<string | null>(null);

  type CompletingState = { kind: "chore"; id: string; notes: string } | { kind: "assignment"; id: string; notes: string };
  let completing = $state<CompletingState | null>(null);

  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  const filteredChores = $derived(
    searchQuery
      ? store.chores.filter((c) => c.name.toLowerCase().includes(searchQuery.toLowerCase()))
      : store.chores,
  );

  function getRoomName(roomId: string): string {
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || `Room (${floor.name})`;
    }
    return "Unknown room";
  }

  function assignmentsForChore(choreId: string): Assignment[] {
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

  function earliestDue(assignments: Assignment[]): string | null {
    const dates = assignments.map((a) => a.nextDueDate).filter(Boolean).sort();
    return dates[0] ?? null;
  }

  function roomsSummary(assignments: Assignment[]): string {
    if (assignments.length === 0) return "—";
    if (assignments.length === 1) {
      const a = assignments[0];
      return a.roomId ? getRoomName(a.roomId) : "🏠 Whole house";
    }
    return `${assignments.length} rooms`;
  }

  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await store.importFromDonetick(importToken.trim());
      importStatus = "done"; importToken = ""; showImportInput = false;
    } catch { importStatus = "error"; }
  }

  async function confirmComplete(): Promise<void> {
    if (!completing) return;
    const c = completing;
    completing = null;
    if (c.kind === "chore") await store.completeChore(c.id, c.notes);
    else await store.completeAssignment(c.id, c.notes);
  }
</script>

<div class="page">
  <div class="toolbar">
    <Input placeholder="🔍 Search…" bind:value={searchQuery} />
    <Button onclick={() => onnewchore?.()}>＋ New chore</Button>
    {#if !showImportInput}
      <Button variant="secondary" onclick={() => { showImportInput = true; }}>Import from Donetick</Button>
    {:else}
      <Input type="password" placeholder="API token" bind:value={importToken} />
      <Button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? "Importing…" : "Import"}
      </Button>
      <Button variant="ghost" onclick={() => { showImportInput = false; }}>Cancel</Button>
      {#if importStatus === "error"}<span class="msg-error">Failed</span>{/if}
      {#if importStatus === "done"}<span class="msg-success">{importCount} imported</span>{/if}
    {/if}
  </div>

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Schedule</th>
          <th>Rooms</th>
          <th>Next due</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each filteredChores as chore (chore.id)}
          {@const assignments = assignmentsForChore(chore.id)}
          {@const nextDue = earliestDue(assignments)}
          {@const isExpanded = expandedHistory === chore.id}
          {@const completingChore = completing?.kind === "chore" && completing.id === chore.id ? completing : null}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { editChore = chore; }}>
            <td class="emoji-cell">{chore.emoji}</td>
            <td class="name-cell">
              {displayName(chore)}{#if chore.scheduleFromDue}&nbsp;<span class="sfd-badge" title="Schedules from due date">📅</span>{/if}
            </td>
            <td>{scheduleLabel(chore)}</td>
            <td>{roomsSummary(assignments)}</td>
            <td>{nextDue ? formatDate(nextDue) : "—"}</td>
            <td class="actions-cell" onclick={(e) => e.stopPropagation()}>
              {#if completingChore}
                <input
                  class="note-input"
                  bind:value={completingChore.notes}
                  placeholder="Note (optional)"
                  onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                />
                <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
                <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
              {:else}
                <button class="icon-btn" title="Mark all done" onclick={() => { completing = { kind: "chore", id: chore.id, notes: "" }; }}>✓</button>
              {/if}
              <button
                class="icon-btn"
                class:active-hist={isExpanded}
                title={isExpanded ? "Hide history" : "Show history & assignments"}
                onclick={() => { expandedHistory = isExpanded ? null : chore.id; }}
              >🕐</button>
            </td>
          </tr>

          {#if isExpanded}
            {@const history = store.getCompletionsForChore(chore.id).slice().reverse()}
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
            <tr class="expand-row" onclick={(e) => e.stopPropagation()}>
              <td colspan="6">
                <div class="expand-body">
                  <div class="assign-section">
                    {#if assignments.length > 0}
                      {#each assignments as a (a.id)}
                        {@const completingAssign = completing?.kind === "assignment" && completing.id === a.id ? completing : null}
                        <div class="assign-row">
                          <span class="assign-where">{a.roomId ? getRoomName(a.roomId) : "🏠 Whole house"}</span>
                          <span class="assign-due">Due: {formatDate(a.nextDueDate)}</span>
                          {#if completingAssign}
                            <input
                              class="note-input"
                              bind:value={completingAssign.notes}
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
                    {:else}
                      <div class="no-assign">Not assigned to any room</div>
                    {/if}
                  </div>

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
                </div>
              </td>
            </tr>
          {/if}
        {/each}

        {#if filteredChores.length === 0}
          <tr>
            <td colspan="6" class="empty">
              {store.chores.length === 0
                ? "No chores yet — click ＋ New chore to get started."
                : "No chores match your search."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <div class="footer">{filteredChores.length} chore{filteredChores.length !== 1 ? "s" : ""}</div>
</div>

<ChoreEditModal chore={editChore} {store} onclose={() => { editChore = null; }} />

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; flex-wrap: wrap;
  }
  .toolbar :global(.ui-input) { flex: 1; min-width: 140px; }
  .msg-error { color: var(--danger); font-size: 11px; }
  .msg-success { color: var(--success); font-size: 11px; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:not(.expand-row):hover td { background: var(--surface-hover); cursor: pointer; }
  .emoji-cell { font-size: 16px; width: 32px; text-align: center; }
  .name-cell { color: var(--text); font-weight: 600; }
  .sfd-badge { font-size: 11px; cursor: help; }
  .actions-cell { white-space: nowrap; text-align: right; }
  .empty { text-align: center; color: var(--text-faint); padding: 32px; }

  .icon-btn {
    padding: 4px 8px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px;
  }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .icon-btn.danger:hover { color: var(--danger); }
  .confirm-btn { background: var(--success) !important; color: var(--accent-contrast) !important; }
  .active-hist { background: var(--surface-hover) !important; color: var(--accent) !important; }

  .note-input {
    padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 12px; width: 120px;
    font-family: var(--font-sans);
  }
  .note-input:focus { outline: none; border-color: var(--accent); }

  .expand-row td { background: var(--surface-alt); padding: 0; cursor: default; }
  .expand-body { padding: 12px 16px; display: flex; gap: 24px; flex-wrap: wrap; }

  .assign-section { display: flex; flex-direction: column; gap: 6px; min-width: 260px; }
  .assign-row { display: flex; align-items: center; gap: 8px; font-size: 12px; flex-wrap: wrap; }
  .assign-where { flex: 1; min-width: 80px; color: var(--text-muted); }
  .assign-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .no-assign { font-size: 11px; color: var(--text-faint); font-style: italic; }

  .history-section { flex: 1; min-width: 220px; }
  .history-title { font-size: 10px; text-transform: uppercase; color: var(--text-faint); letter-spacing: 0.06em; margin-bottom: 6px; }
  .no-history { font-size: 11px; color: var(--text-faint); font-style: italic; }
  .history-row { display: flex; align-items: baseline; gap: 10px; padding: 3px 0; font-size: 11px; flex-wrap: wrap; }
  .hist-date { color: var(--text-muted); white-space: nowrap; flex-shrink: 0; }
  .hist-due { color: var(--text-faint); white-space: nowrap; }
  .hist-notes { color: var(--text-muted); font-style: italic; }

  .footer { padding: 6px 12px; font-size: 11px; color: var(--text-faint); border-top: 1px solid var(--border); flex-shrink: 0; }
</style>
