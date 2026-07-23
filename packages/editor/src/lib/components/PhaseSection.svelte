<!-- packages/editor/src/lib/components/PhaseSection.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    store: BuildStore;
    onopentask: (taskId: string) => void;
  }
  let { store, onopentask }: Props = $props();

  let expandedPhaseId = $state<string | null>(null);

  function resolveLabel(key: string | null, override: string | null): string {
    if (override) return override;
    if (key) return $_(key);
    return "";
  }

  function toggle(phaseId: string): void {
    expandedPhaseId = expandedPhaseId === phaseId ? null : phaseId;
  }

  const sortedPhases = $derived([...store.phases].sort((a, b) => a.displayOrder - b.displayOrder));
</script>

{#if sortedPhases.length === 0}
  <p class="empty">{$_('build.page.noPhases')}</p>
{:else}
  {#each sortedPhases as phase (phase.id)}
    {@const phaseTasks = store.phaseTasks(phase.id).sort((a, b) => a.displayOrder - b.displayOrder)}
    {@const progress = store.phaseProgress(phase.id)}
    <div class="phase-section">
      <Card>
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
        <div class="phase-header" role="button" tabindex="0" onclick={() => toggle(phase.id)}>
          <span class="chevron">{expandedPhaseId === phase.id ? "▼" : "▶"}</span>
          <span class="phase-name">{resolveLabel(phase.nameKey, phase.nameOverride)}</span>
          <span class="phase-status">{$_(`build.phaseStatus.${phase.status === "in_progress" ? "inProgress" : phase.status}`)}</span>
          <span class="phase-count">{$_('build.page.taskCount', { values: { n: phaseTasks.length } })}</span>
          <div class="progress-track"><div class="progress-fill" style="width:{progress * 100}%"></div></div>
        </div>
        {#if expandedPhaseId === phase.id}
          <div class="phase-tasks">
            {#each phaseTasks as task (task.id)}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
              <div class="task-row" role="button" tabindex="0" onclick={() => onopentask(task.id)}>
                <span class="task-title">{resolveLabel(task.titleKey, task.titleOverride)}</span>
                <span class="task-status">{$_(`build.taskStatus.${task.status === "in_progress" ? "inProgress" : task.status === "not_started" ? "notStarted" : task.status}`)}</span>
                <span class="task-due">{task.plannedDueDate ?? "—"}</span>
                <span class="task-contractor">{task.contractorId ?? "—"}</span>
              </div>
            {/each}
          </div>
        {/if}
      </Card>
    </div>
  {/each}
{/if}

<style>
  .empty { font-size: 12px; color: var(--text-faint); }
  .phase-section { margin-bottom: var(--space-2); }
  .phase-header {
    display: flex; align-items: center; gap: 10px; cursor: pointer;
  }
  .chevron { font-size: 9px; color: var(--text-faint); width: 12px; }
  .phase-name { flex: 1; font-size: 13px; font-weight: 600; }
  .phase-status { font-size: 11px; color: var(--text-muted); }
  .phase-count { font-size: 11px; color: var(--text-faint); }
  .progress-track { width: 80px; height: 6px; background: var(--surface-alt); border-radius: 999px; overflow: hidden; }
  .progress-fill { height: 100%; background: var(--accent); }
  .phase-tasks { margin-top: var(--space-3); display: flex; flex-direction: column; gap: 4px; }
  .task-row {
    display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: var(--radius-sm);
    cursor: pointer; font-size: 12px;
  }
  .task-row:hover { background: var(--surface-hover); }
  .task-title { flex: 1; }
  .task-status, .task-due, .task-contractor { color: var(--text-muted); font-size: 11px; }
</style>
