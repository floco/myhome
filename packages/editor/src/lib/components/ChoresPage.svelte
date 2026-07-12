<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import ChoreEditModal from "./ChoreEditModal.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";

  type ChoreStore = ReturnType<typeof createChoreStore>;
  type Assignment = ChoreStore["assignments"][number];

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
    onnewchore?: () => void;
    onplaceonmap?: (choreId: string) => void;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }

  let { store, floorStore, onnewchore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();

  let editChore = $state<Chore | null>(null);

  $effect(() => {
    if (selectedItemId) {
      const found = store.chores.find((c) => c.id === selectedItemId);
      if (found) {
        editChore = found;
        onclearselection?.();
      }
    }
  });
  let searchQuery = $state("");
  let roomFilter = $state("");
  let scheduleFilter = $state("");
  let dueFilter = $state<"all" | "attention">("attention");
  let expandedHistory = $state<string | null>(null);

  function needsAttention(assignments: Assignment[]): boolean {
    if (assignments.length === 0) return false;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() + 7);
    return assignments.some((a) => a.nextDueDate && new Date(a.nextDueDate) <= cutoff);
  }

  type CompletingState = { kind: "chore"; id: string; notes: string } | { kind: "assignment"; id: string; notes: string };
  let completing = $state<CompletingState | null>(null);

  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  const allRooms = $derived(floorStore.floors.flatMap((f) => f.rooms));

  function scheduleCategory(chore: Chore): string {
    const { frequencyType: ft, frequency: n, frequencyMetadata: meta } = chore;
    const unit = (meta as Record<string, string>)?.unit ?? "days";
    if (ft === "days_of_the_week" || ft === "weekly") return "weekly";
    if (ft === "day_of_the_month" || ft === "monthly") return "monthly";
    if (ft === "yearly") return "yearly";
    if (ft === "interval") {
      if (unit === "years") return "yearly";
      if (unit === "months") return "monthly";
      if (unit === "weeks") return "weekly";
      if (n <= 1) return "daily";
      if (n < 14) return "weekly";
      if (n < 60) return "monthly";
      return "yearly";
    }
    return "other";
  }

  const filteredChores = $derived(
    store.chores.filter((c) => {
      if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (scheduleFilter && scheduleCategory(c) !== scheduleFilter) return false;
      const assignments = store.assignments.filter((a) => a.choreId === c.id);
      if (roomFilter && !assignments.some((a) => a.roomId === roomFilter)) return false;
      if (dueFilter === "attention" && !needsAttention(assignments)) return false;
      return true;
    }),
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
    <select class="native-input" bind:value={roomFilter}>
      <option value="">All rooms</option>
      {#each allRooms as room}
        <option value={room.id}>{room.label}</option>
      {/each}
    </select>
    <select class="native-input" bind:value={scheduleFilter}>
      <option value="">All schedules</option>
      <option value="daily">Daily</option>
      <option value="weekly">Weekly</option>
      <option value="monthly">Monthly</option>
      <option value="yearly">Yearly</option>
    </select>
    <div class="filter-toggle">
      <button class="toggle-btn" class:active={dueFilter === "all"} title="All chores" onclick={() => { dueFilter = "all"; }}>☰</button>
      <button class="toggle-btn" class:active={dueFilter === "attention"} title="Needs attention" onclick={() => { dueFilter = "attention"; }}>⚠</button>
    </div>
    <Button onclick={() => onnewchore?.()}>＋ Add chore</Button>
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
    {#snippet expandCell(chore: Chore)}
      <button
        class="expand-btn"
        onclick={(e) => { e.stopPropagation(); expandedHistory = expandedHistory === chore.id ? null : chore.id; }}
      >{expandedHistory === chore.id ? "▼" : "▶"}</button>
    {/snippet}
    {#snippet emojiCell(chore: Chore)}
      {chore.emoji}
    {/snippet}
    {#snippet nameCell(chore: Chore)}
      {displayName(chore)}{#if chore.scheduleFromDue}&nbsp;<span class="sfd-badge" title="Schedules from due date">📅</span>{/if}
    {/snippet}
    {#snippet scheduleCell(chore: Chore)}
      {scheduleLabel(chore)}
    {/snippet}
    {#snippet roomsCell(chore: Chore)}
      {roomsSummary(assignmentsForChore(chore.id))}
    {/snippet}
    {#snippet nextDueCell(chore: Chore)}
      {@const nextDue = earliestDue(assignmentsForChore(chore.id))}
      {nextDue ? formatDate(nextDue) : "—"}
    {/snippet}
    {#snippet actionsCell(chore: Chore)}
      {@const completingChore = completing?.kind === "chore" && completing.id === chore.id ? completing : null}
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
      <button class="icon-btn" title="Delay all assignments by 1 week" onclick={() => store.delayChore(chore.id, 7)}>⏭</button>
    {/snippet}
    {#snippet assignmentsExpanded(chore: Chore)}
      {@const assignments = assignmentsForChore(chore.id)}
      <div class="expand-body">
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
              <button class="icon-btn" title="Delay by 1 week" onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
            </div>
          {/each}
        {:else}
          <div class="no-assign">Not assigned to any room</div>
        {/if}
      </div>
    {/snippet}

    <SortableTable
      columns={[
        { key: "expand", label: "", sortable: false, cellClass: "expand-cell", cell: expandCell },
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "name", label: "Name", sortValue: (c) => displayName(c), cellClass: "name-cell", cell: nameCell },
        { key: "schedule", label: "Schedule", sortValue: (c) => scheduleLabel(c), cell: scheduleCell },
        { key: "rooms", label: "Rooms", sortValue: (c) => roomsSummary(assignmentsForChore(c.id)), cell: roomsCell },
        { key: "nextDue", label: "Next due", sortValue: (c) => { const d = earliestDue(assignmentsForChore(c.id)); return d ? new Date(d) : null; }, cell: nextDueCell },
        { key: "actions", label: "", sortable: false, cellClass: "actions-cell", stopRowClick: true, cell: actionsCell },
      ] as Column<Chore>[]}
      rows={filteredChores}
      rowKey={(chore) => chore.id}
      rowClick={(chore) => { editChore = chore; }}
      isRowExpanded={(chore) => expandedHistory === chore.id}
      expandedRow={assignmentsExpanded}
      emptyMessage={store.chores.length === 0
        ? "No chores yet — click ＋ Add chore to get started."
        : dueFilter === "attention"
          ? "No chores need attention right now."
          : "No chores match your filters."}
    />
  </div>

  <div class="footer">{filteredChores.length} chore{filteredChores.length !== 1 ? "s" : ""}</div>
</div>

{#if editChore}
  <ChoreEditModal chore={editChore} {store} rooms={allRooms} onclose={() => { editChore = null; }} onplaceonmap={onplaceonmap ? (id) => { editChore = null; onplaceonmap!(id); } : undefined} />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; flex-wrap: wrap;
  }
  .toolbar :global(.ui-input) { flex: 1; min-width: 140px; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-toggle { display: flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; flex-shrink: 0; }
  .toggle-btn { padding: 6px 12px; border: none; background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px; white-space: nowrap; }
  .toggle-btn:not(:last-child) { border-right: 1px solid var(--border); }
  .toggle-btn.active { background: var(--accent); color: var(--accent-contrast); }
  .toggle-btn:not(.active):hover { background: var(--surface-hover); color: var(--text); }
  .msg-error { color: var(--danger); font-size: 11px; }
  .msg-success { color: var(--success); font-size: 11px; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  .sfd-badge { font-size: 11px; cursor: help; }
  :global(.actions-cell) { white-space: nowrap; text-align: right; }

  .icon-btn {
    padding: 8px 14px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 15px;
    min-height: 38px;
  }
  :global(.expand-cell) { width: 20px; padding: 0 4px; text-align: center; }
  .expand-btn { background: none; border: none; cursor: pointer; color: var(--text-faint); font-size: 9px; padding: 2px 4px; line-height: 1; }
  .expand-btn:hover { color: var(--text); }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .icon-btn.danger:hover { color: var(--danger); }
  .confirm-btn { background: var(--success) !important; color: var(--accent-contrast) !important; }

  .note-input {
    padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 12px; width: 120px;
    font-family: var(--font-sans);
  }
  .note-input:focus { outline: none; border-color: var(--accent); }

  .expand-body { padding: 10px 16px; display: flex; flex-direction: column; gap: 6px; }

  .assign-row { display: flex; align-items: center; gap: 8px; font-size: 12px; flex-wrap: wrap; }
  .assign-row .icon-btn { padding: 4px 8px; font-size: 13px; min-height: 28px; }
  .assign-where { flex: 1; min-width: 80px; color: var(--text-muted); }
  .assign-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .no-assign { font-size: 11px; color: var(--text-faint); font-style: italic; }

  .footer { padding: 6px 12px; font-size: 11px; color: var(--text-faint); border-top: 1px solid var(--border); flex-shrink: 0; }
</style>
