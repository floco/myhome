<!-- packages/editor/src/lib/components/PhaseSection.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore, BuildPhase } from "../buildStore.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    store: BuildStore;
    onopentask: (taskId: string) => void;
  }
  let { store, onopentask }: Props = $props();

  let expandedPhaseId = $state<string | null>(null);
  let searchQuery = $state("");

  function resolveLabel(key: string | null, override: string | null): string {
    if (override) return override;
    if (key) return $_(key);
    return "";
  }

  function toggle(phaseId: string): void {
    expandedPhaseId = expandedPhaseId === phaseId ? null : phaseId;
  }

  function phaseStatusLabel(status: BuildPhase["status"]): string {
    const key = status === "in_progress" ? "inProgress" : status === "not_started" ? "notStarted" : status;
    return $_(`build.phaseStatus.${key}`);
  }

  function taskStatusLabel(status: string): string {
    const key = status === "in_progress" ? "inProgress" : status === "not_started" ? "notStarted" : status;
    return $_(`build.taskStatus.${key}`);
  }

  const filteredPhases = $derived(
    [...store.phases]
      .sort((a, b) => a.displayOrder - b.displayOrder)
      .filter((phase) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        if (resolveLabel(phase.nameKey, phase.nameOverride).toLowerCase().includes(q)) return true;
        return store.phaseTasks(phase.id).some((t) => resolveLabel(t.titleKey, t.titleOverride).toLowerCase().includes(q));
      })
  );
</script>

<div class="toolbar">
  <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
</div>

<div class="table-wrapper">
  {#snippet expandCell(phase: BuildPhase)}
    <button
      class="expand-btn"
      onclick={(e) => { e.stopPropagation(); toggle(phase.id); }}
    >{expandedPhaseId === phase.id ? "▼" : "▶"}</button>
  {/snippet}
  {#snippet nameCell(phase: BuildPhase)}
    {resolveLabel(phase.nameKey, phase.nameOverride)}
  {/snippet}
  {#snippet statusCell(phase: BuildPhase)}
    {phaseStatusLabel(phase.status)}
  {/snippet}
  {#snippet countCell(phase: BuildPhase)}
    {$_('build.page.taskCount', { values: { n: store.phaseTasks(phase.id).length } })}
  {/snippet}
  {#snippet progressCell(phase: BuildPhase)}
    {@const progress = store.phaseProgress(phase.id)}
    <div class="progress-track"><div class="progress-fill" style="width:{progress * 100}%"></div></div>
  {/snippet}
  {#snippet phaseTasksExpanded(phase: BuildPhase)}
    {@const phaseTasks = store.phaseTasks(phase.id).sort((a, b) => a.displayOrder - b.displayOrder)}
    <div class="phase-tasks">
      {#each phaseTasks as task (task.id)}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
        <div class="task-row" role="button" tabindex="0" onclick={() => onopentask(task.id)}>
          <span class="task-title">{resolveLabel(task.titleKey, task.titleOverride)}</span>
          <span class="task-status">{taskStatusLabel(task.status)}</span>
          <span class="task-due">{task.plannedDueDate ?? "—"}</span>
          <span class="task-contractor">{task.contractorId ?? "—"}</span>
        </div>
      {/each}
    </div>
  {/snippet}

  <SortableTable
    columns={[
      { key: "expand", label: "", sortable: false, cellClass: "expand-cell", cell: expandCell },
      { key: "name", label: $_('build.page.phasesTab'), sortValue: (p) => resolveLabel(p.nameKey, p.nameOverride), cellClass: "name-cell", cell: nameCell },
      { key: "status", label: $_('build.dashboard.status'), sortValue: (p) => p.status, cell: statusCell },
      { key: "count", label: "", sortable: false, cellClass: "count-cell", cell: countCell },
      { key: "progress", label: "", sortable: false, cellClass: "progress-cell", cell: progressCell },
    ] as Column<BuildPhase>[]}
    rows={filteredPhases}
    rowKey={(phase) => phase.id}
    rowClick={(phase) => toggle(phase.id)}
    isRowExpanded={(phase) => expandedPhaseId === phase.id}
    expandedRow={phaseTasksExpanded}
    emptyMessage={store.phases.length === 0 ? $_('build.page.noPhases') : $_('chores.page.emptyNoMatch')}
  />
</div>

<style>
  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .toolbar :global(.ui-input) { flex: 1; min-width: 140px; max-width: 320px; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.expand-cell) { width: 20px; padding: 0 4px; text-align: center; }
  .expand-btn { background: none; border: none; cursor: pointer; color: var(--text-faint); font-size: 9px; padding: 2px 4px; line-height: 1; }
  .expand-btn:hover { color: var(--text); }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  :global(.count-cell) { color: var(--text-faint); white-space: nowrap; }
  :global(.progress-cell) { width: 100px; }
  .progress-track { width: 80px; height: 6px; background: var(--surface-alt); border-radius: 999px; overflow: hidden; }
  .progress-fill { height: 100%; background: var(--accent); }

  .phase-tasks { display: flex; flex-direction: column; gap: 4px; padding: var(--space-2) var(--space-3); }
  .task-row {
    display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: var(--radius-sm);
    cursor: pointer; font-size: 12px;
  }
  .task-row:hover { background: var(--surface-hover); }
  .task-title { flex: 1; }
  .task-status, .task-due, .task-contractor { color: var(--text-muted); font-size: 11px; }
</style>
