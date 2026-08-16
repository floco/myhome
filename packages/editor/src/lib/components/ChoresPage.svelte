<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";
  import { scheduleLabel } from "../choreStore.svelte";
  import { choreFilterState } from "../choreFilterState.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import ChoreEditModal from "./ChoreEditModal.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import HorizontalBarChart from "./HorizontalBarChart.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
  import { formatDate } from "../dateFormat";
  import ChoreCompleteModal from "./ChoreCompleteModal.svelte";
  import type { Point } from "@myhome/geometry";

  type FullChoreStore = ReturnType<typeof createChoreStore>;
  type Assignment = FullChoreStore["assignments"][number];
  // Only what this component uses directly, plus what it forwards through
  // to ChoreEditModal's own (narrower) store prop -- not the whole store.
  type ChoreStore = Pick<FullChoreStore,
    | "chores" | "assignments" | "completeChore" | "delayChore" | "getProgress"
    | "updateChore" | "deleteChore" | "uploadAttachment" | "deleteAttachment"
    | "getCompletionsForChore" | "deleteCompletion" | "createAssignment"
    | "updateAssignmentLabel" | "deleteAssignment" | "delayAssignment"
    | "completeAssignment" | "previewNextDue"
  >;

  interface Props {
    store: ChoreStore;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string; polygon: Point[] | null }> }> };
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
  let filterModalOpen = $state(false);
  let healthFilter = $state<HealthBucket | null>(null);
  const filtersActive = $derived(roomFilter !== "" || scheduleFilter !== "");

  function needsAttention(assignments: Assignment[]): boolean {
    if (assignments.length === 0) return true; // unplaced chore -- needs a room before it can be tracked
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() + 7);
    return assignments.some((a) => a.nextDueDate && new Date(a.nextDueDate) <= cutoff);
  }

  type CompletingState = { kind: "chore"; id: string; title: string };
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
  const overduePct = $derived(totalAssignments > 0 ? Math.round((overdueCount / totalAssignments) * 100) : 0);
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
    const weekPattern = (meta as Record<string, string>)?.weekPattern;
    if (ft === "daily") return "daily";
    if (ft === "adaptive") return "adaptive";
    if (ft === "days_of_the_week" && (weekPattern === "week_of_month" || weekPattern === "week_of_quarter")) return "nth_weekday";
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

  function choreHealthBuckets(chore: Chore): HealthBucket[] {
    return store.assignments
      .filter((a) => a.choreId === chore.id)
      .map((a) => healthBucket(store.getProgress(a, chore)));
  }

  function toggleHealthFilter(bucket: HealthBucket): void {
    healthFilter = healthFilter === bucket ? null : bucket;
  }

  const filteredChores = $derived(
    store.chores.filter((c) => {
      if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (scheduleFilter && scheduleCategory(c) !== scheduleFilter) return false;
      const assignments = store.assignments.filter((a) => a.choreId === c.id);
      if (roomFilter && !assignments.some((a) => a.roomId === roomFilter)) return false;
      if (choreFilterState.dueFilter === "attention" && !needsAttention(assignments)) return false;
      if (healthFilter && !choreHealthBuckets(c).includes(healthFilter)) return false;
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

  async function confirmComplete(notes: string, completedOn?: string): Promise<void> {
    if (!completing) return;
    const c = completing;
    completing = null;
    if (completedOn) await store.completeChore(c.id, notes, completedOn);
    else await store.completeChore(c.id, notes);
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
      <Card style="flex: 2 1 260px; min-width: 0;">
        <div class="chart-label">{$_('chores.page.scheduleHealth')}</div>
        <HorizontalBarChart segments={healthBreakdown} activeId={healthFilter} onsegmentclick={(id) => toggleHealthFilter(id as HealthBucket)} />
      </Card>
      <div class="stat-tiles">
        <StatTile label={$_('chores.page.active')} value={totalAssignments} active={healthFilter === null} onclick={() => { healthFilter = null; }} />
        <StatTile label={$_('chores.page.overdue')} value={`${overduePct}%`} variant="danger" active={healthFilter === "overdue"} onclick={() => toggleHealthFilter("overdue")} />
        <StatTile label={$_('chores.page.onTrack')} value={`${onTrackPct}%`} variant="success" active={healthFilter === "on-track"} onclick={() => toggleHealthFilter("on-track")} />
      </div>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <div class="filter-toggle">
        <button class="toggle-btn" class:active={choreFilterState.dueFilter === "all"} title={$_('chores.page.allChores')} onclick={() => { choreFilterState.dueFilter = "all"; }}>☰</button>
        <button class="toggle-btn" class:active={choreFilterState.dueFilter === "attention"} title={$_('chores.page.needsAttentionTitle')} onclick={() => { choreFilterState.dueFilter = "attention"; }}>⚠</button>
      </div>
      <Button iconOnly title={$_('chores.page.addChore')} onclick={() => onnewchore?.()}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
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
          <option value="nth_weekday">{$_('chores.schedule.nthWeekday')}</option>
          <option value="yearly">{$_('chores.schedule.yearly')}</option>
          <option value="adaptive">{$_('chores.schedule.adaptive')}</option>
        </select>
      </div>
    </Modal>

    <div class="table-wrapper">
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
        <button class="icon-btn" title={$_('chores.page.markAllDone')} onclick={() => { completing = { kind: "chore", id: chore.id, title: `${chore.emoji} ${displayName(chore)}` }; }}>✓</button>
        <button class="icon-btn" title={$_('chores.page.delayAllByWeek')} onclick={() => store.delayChore(chore.id, 7)}>⏭</button>
      {/snippet}
      <SortableTable
        columns={[
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "name", label: $_('chores.editModal.name'), sortValue: (c) => displayName(c), cellClass: "name-cell", cell: nameCell },
          { key: "schedule", label: $_('chores.page.schedule'), sortValue: (c) => scheduleLabel(c), cell: scheduleCell, hideBelow: "mobile" },
          { key: "rooms", label: $_('chores.page.rooms'), sortValue: (c) => roomsSummary(assignmentsForChore(c.id)), cell: roomsCell, hideBelow: "tablet" },
          { key: "nextDue", label: $_('chores.page.nextDue'), sortValue: (c) => { const d = earliestDue(assignmentsForChore(c.id)); return d ? new Date(d) : null; }, cell: nextDueCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions-cell", stopRowClick: true, cell: actionsCell },
        ] as Column<Chore>[]}
        rows={filteredChores}
        rowKey={(chore) => chore.id}
        rowClick={(chore) => { editChore = chore; }}
        defaultSort={{ key: "nextDue", direction: "asc" }}
        emptyMessage={store.chores.length === 0
          ? $_('chores.page.emptyNoChores')
          : choreFilterState.dueFilter === "attention"
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

{#if completing}
  <ChoreCompleteModal title={completing.title} onclose={() => { completing = null; }} onconfirm={confirmComplete} />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: stretch; padding: var(--space-4); flex-shrink: 0; }
  .stat-tiles { display: flex; flex-wrap: nowrap; gap: var(--space-3); flex: 1 1 300px; min-width: 0; }
  .stat-tiles :global(.ui-stat-tile) { flex: 1 1 0; min-width: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }

  @media (max-width: 700px) {
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }

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
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }

  .footer { padding: 6px 12px; font-size: 11px; color: var(--text-faint); border-top: 1px solid var(--border); flex-shrink: 0; }
</style>
