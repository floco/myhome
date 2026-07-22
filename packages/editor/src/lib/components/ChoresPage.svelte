<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import ChoreEditModal from "./ChoreEditModal.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import HorizontalBarChart from "./HorizontalBarChart.svelte";

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

  const allRooms = $derived(floorStore.floors.flatMap((f) => f.rooms));

  type HealthBucket = "on-track" | "due-soon" | "overdue";

  const HEALTH_META: Record<HealthBucket, { emoji: string; color: string }> = {
    "on-track": { emoji: "🟢", color: "#4caf50" },
    "due-soon": { emoji: "🟠", color: "#ff9800" },
    overdue: { emoji: "🔴", color: "#f44336" },
  };

  function healthBucket(pct: number): HealthBucket {
    if (pct > 0.5) return "on-track";
    if (pct > 0.25) return "due-soon";
    return "overdue";
  }

  const assignmentHealth = $derived(
    store.assignments
      .map((a) => {
        const chore = store.chores.find((c) => c.id === a.choreId);
        return chore ? healthBucket(store.getProgress(a, chore)) : null;
      })
      .filter((h): h is HealthBucket => h !== null)
  );

  const totalAssignments = $derived(assignmentHealth.length);
  const overdueCount = $derived(assignmentHealth.filter((h) => h === "overdue").length);
  const onTrackCount = $derived(assignmentHealth.filter((h) => h === "on-track").length);
  const onTrackPct = $derived(totalAssignments > 0 ? Math.round((onTrackCount / totalAssignments) * 100) : 0);

  const HEALTH_LABEL_KEY: Record<HealthBucket, string> = {
    "on-track": "onTrack",
    "due-soon": "dueSoon",
    overdue: "overdue",
  };

  const healthBreakdown = $derived(
    (["on-track", "due-soon", "overdue"] as HealthBucket[])
      .map((bucket) => {
        const count = assignmentHealth.filter((h) => h === bucket).length;
        const meta = HEALTH_META[bucket];
        return {
          id: bucket,
          label: $_(`chores.page.health.${HEALTH_LABEL_KEY[bucket]}`),
          emoji: meta.emoji,
          color: meta.color,
          valueLabel: `${count}`,
          pct: totalAssignments > 0 ? (count / totalAssignments) * 100 : 0,
          count,
        };
      })
      .filter((b) => b.count > 0)
  );

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
      if (room) return room.label || $_('chores.list.roomInFloor', { values: { floor: floor.name } });
    }
    return $_('chores.list.unknownRoom');
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
      return a.roomId ? getRoomName(a.roomId) : `🏠 ${$_('chores.list.wholeHouse')}`;
    }
    return $_('chores.page.roomCount', { values: { n: assignments.length } });
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

  {#if totalAssignments === 0}
    <div class="empty-charts">
      <span class="empty-icon">✅</span>
      <p>{$_('chores.page.emptyCharts')}</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="bar-area">
            <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
            <HorizontalBarChart segments={healthBreakdown} />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">{$_('chores.page.atAGlance')}</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">{$_('chores.page.active')}</div>
                <div class="stat-value">{totalAssignments}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('chores.page.overdue')}</div>
                <div class="stat-value overdue">{overdueCount}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('chores.page.onTrack')}</div>
                <div class="stat-value ontrack">{onTrackPct}%</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-input" bind:value={roomFilter}>
        <option value="">{$_('chores.page.allRooms')}</option>
        {#each allRooms as room}
          <option value={room.id}>{room.label}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={scheduleFilter}>
        <option value="">{$_('chores.page.allSchedules')}</option>
        <option value="daily">{$_('chores.schedule.daily')}</option>
        <option value="weekly">{$_('chores.schedule.weekly')}</option>
        <option value="monthly">{$_('chores.schedule.monthly')}</option>
        <option value="yearly">{$_('chores.schedule.yearly')}</option>
      </select>
      <div class="filter-toggle">
        <button class="toggle-btn" class:active={dueFilter === "all"} title={$_('chores.page.allChores')} onclick={() => { dueFilter = "all"; }}>☰</button>
        <button class="toggle-btn" class:active={dueFilter === "attention"} title={$_('chores.page.needsAttentionTitle')} onclick={() => { dueFilter = "attention"; }}>⚠</button>
      </div>
      <Button onclick={() => onnewchore?.()}>＋ {$_('chores.page.addChore')}</Button>
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
        {displayName(chore)}{#if chore.scheduleFromDue}&nbsp;<span class="sfd-badge" title={$_('chores.page.schedulesFromDueDate')}>📅</span>{/if}
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
            placeholder={$_('chores.row.notePlaceholder')}
            onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
          />
          <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
          <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
        {:else}
          <button class="icon-btn" title={$_('chores.page.markAllDone')} onclick={() => { completing = { kind: "chore", id: chore.id, notes: "" }; }}>✓</button>
        {/if}
        <button class="icon-btn" title={$_('chores.page.delayAllByWeek')} onclick={() => store.delayChore(chore.id, 7)}>⏭</button>
      {/snippet}
      {#snippet assignmentsExpanded(chore: Chore)}
        {@const assignments = assignmentsForChore(chore.id)}
        <div class="expand-body">
          {#if assignments.length > 0}
            {#each assignments as a (a.id)}
              {@const completingAssign = completing?.kind === "assignment" && completing.id === a.id ? completing : null}
              <div class="assign-row">
                <span class="assign-where">{a.roomId ? getRoomName(a.roomId) : `🏠 ${$_('chores.list.wholeHouse')}`}</span>
                <span class="assign-due">{$_('chores.badgePopup.due')}: {formatDate(a.nextDueDate)}</span>
                {#if completingAssign}
                  <input
                    class="note-input"
                    bind:value={completingAssign.notes}
                    placeholder={$_('chores.row.notePlaceholder')}
                    onkeydown={(e) => { if (e.key === "Enter") confirmComplete(); if (e.key === "Escape") completing = null; }}
                  />
                  <button class="icon-btn confirm-btn" onclick={confirmComplete}>✓</button>
                  <button class="icon-btn" onclick={() => { completing = null; }}>✕</button>
                {:else}
                  <button class="icon-btn" onclick={() => { completing = { kind: "assignment", id: a.id, notes: "" }; }}>✓</button>
                {/if}
                <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
                <button class="icon-btn" title={$_('chores.page.delayByWeek')} onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
              </div>
            {/each}
          {:else}
            <div class="no-assign">{$_('chores.page.notAssigned')}</div>
          {/if}
        </div>
      {/snippet}

      <SortableTable
        columns={[
          { key: "expand", label: "", sortable: false, cellClass: "expand-cell", cell: expandCell },
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "name", label: $_('chores.editModal.name'), sortValue: (c) => displayName(c), cellClass: "name-cell", cell: nameCell },
          { key: "schedule", label: $_('chores.page.schedule'), sortValue: (c) => scheduleLabel(c), cell: scheduleCell },
          { key: "rooms", label: $_('chores.page.rooms'), sortValue: (c) => roomsSummary(assignmentsForChore(c.id)), cell: roomsCell },
          { key: "nextDue", label: $_('chores.page.nextDue'), sortValue: (c) => { const d = earliestDue(assignmentsForChore(c.id)); return d ? new Date(d) : null; }, cell: nextDueCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions-cell", stopRowClick: true, cell: actionsCell },
        ] as Column<Chore>[]}
        rows={filteredChores}
        rowKey={(chore) => chore.id}
        rowClick={(chore) => { editChore = chore; }}
        isRowExpanded={(chore) => expandedHistory === chore.id}
        expandedRow={assignmentsExpanded}
        emptyMessage={store.chores.length === 0
          ? $_('chores.page.emptyNoChores')
          : dueFilter === "attention"
            ? $_('chores.page.emptyNoneNeedAttention')
            : $_('chores.page.emptyNoMatch')}
      />
    </div>

    <div class="footer">{$_('chores.page.choreCount', { values: { n: filteredChores.length } })}</div>
    </Card>
  </div>
</div>

{#if editChore}
  <ChoreEditModal chore={editChore} {store} rooms={allRooms} onclose={() => { editChore = null; }} onplaceonmap={onplaceonmap ? (id) => { editChore = null; onplaceonmap!(id); } : undefined} />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: center; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .bar-area { flex: 1; min-width: 0; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .stats-area { flex: 1; min-width: 0; }
  .stat-chips-col { display: flex; flex-flow: row wrap; gap: 8px; }
  .stat-chip {
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
  .stat-value.overdue { color: #f44336; }
  .stat-value.ontrack { color: #4caf50; }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

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
