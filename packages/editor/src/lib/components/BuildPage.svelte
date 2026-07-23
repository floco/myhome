<!-- packages/editor/src/lib/components/BuildPage.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";
  import Button from "./ui/Button.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import PhaseSection from "./PhaseSection.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    store: BuildStore;
    onopentask: (taskId: string) => void;
  }
  let { store, onopentask }: Props = $props();

  let activeTab = $state<"dashboard" | "phases">("dashboard");
  let starting = $state(false);
  let startError = $state<string | null>(null);

  async function handleStart(): Promise<void> {
    starting = true; startError = null;
    try {
      await store.startProject();
    } catch (e) {
      startError = e instanceof Error ? e.message : $_('build.modal.saveFailed');
    } finally {
      starting = false;
    }
  }

  function resolveLabel(key: string | null, override: string | null): string {
    if (override) return override;
    if (key) return $_(key);
    return "";
  }

  const currentPhase = $derived(
    store.phases.find((p) => p.status === "in_progress") ?? store.phases.find((p) => p.status !== "completed") ?? null
  );

  const overdueAndUpcoming = $derived(
    store.tasks
      .filter((t) => t.status !== "completed" && t.plannedDueDate)
      .sort((a, b) => (a.plannedDueDate! < b.plannedDueDate! ? -1 : 1))
      .slice(0, 5)
  );

  const upcomingValidations = $derived(
    store.tasks.filter((t) => t.validationRequired && t.validationStatus === "pending_validation").slice(0, 5)
  );

  function fmtMoney(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " €";
  }
</script>

{#if !store.project}
  <div class="start-card">
    <Card>
      <h2>{$_('build.page.startTitle')}</h2>
      <p>{$_('build.page.startDescription')}</p>
      {#if startError}<div class="start-error">{startError}</div>{/if}
      <Button variant="primary" disabled={starting} onclick={handleStart}>{$_('build.page.startButton')}</Button>
    </Card>
  </div>
{:else}
  <Tabs
    tabs={[
      { id: "dashboard", label: $_('build.page.dashboardTab') },
      { id: "phases", label: $_('build.page.phasesTab') },
    ]}
    active={activeTab}
    onchange={(id) => { activeTab = id as "dashboard" | "phases"; }}
  />

  {#if activeTab === "dashboard"}
    <div class="stat-row">
      <StatTile value={$_(`build.projectStatus.${store.project.status === "in_progress" ? "inProgress" : store.project.status === "on_hold" ? "onHold" : store.project.status}`)} label={$_('build.dashboard.status')} />
      <StatTile value={currentPhase ? resolveLabel(currentPhase.nameKey, currentPhase.nameOverride) : "—"} label={$_('build.dashboard.currentPhase')} />
      <StatTile value={`${Math.round(store.projectProgress * 100)}%`} label={$_('build.dashboard.percentComplete')} />
      <StatTile value={fmtMoney(store.projectBudget.planned)} label={$_('build.dashboard.plannedBudget')} />
      <StatTile value={fmtMoney(store.projectBudget.actual)} label={$_('build.dashboard.actualCost')} />
    </div>

    <div class="dash-row">
      <Card>
        <h3>{$_('build.dashboard.overdueTasks')}</h3>
        {#if overdueAndUpcoming.length === 0}
          <p class="empty">{$_('build.dashboard.noOverdue')}</p>
        {:else}
          <ul class="task-list">
            {#each overdueAndUpcoming as task (task.id)}
              <li>
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
                <span class="task-link" role="button" tabindex="0" onclick={() => onopentask(task.id)}>
                  {resolveLabel(task.titleKey, task.titleOverride)} — {task.plannedDueDate}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      </Card>
      <Card>
        <h3>{$_('build.dashboard.upcomingValidations')}</h3>
        {#if upcomingValidations.length === 0}
          <p class="empty">{$_('build.dashboard.noValidationsPending')}</p>
        {:else}
          <ul class="task-list">
            {#each upcomingValidations as task (task.id)}
              <li>
                <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
                <span class="task-link" role="button" tabindex="0" onclick={() => onopentask(task.id)}>
                  {resolveLabel(task.titleKey, task.titleOverride)}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      </Card>
    </div>
  {:else}
    <PhaseSection {store} {onopentask} />
  {/if}
{/if}

<style>
  .start-card { display: flex; justify-content: center; padding: var(--space-4); }
  .start-card :global(.ui-card) { max-width: 480px; text-align: center; }
  .start-error { color: var(--danger); font-size: 12px; margin: 8px 0; }
  .stat-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-3); margin-bottom: var(--space-4); }
  .dash-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
  .dash-row h3 { margin: 0 0 var(--space-2); font-size: 13px; }
  .empty { font-size: 12px; color: var(--text-faint); }
  .task-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .task-link { cursor: pointer; font-size: 12px; color: var(--text); }
  .task-link:hover { text-decoration: underline; }
  @media (max-width: 900px) {
    .stat-row { grid-template-columns: repeat(2, 1fr); }
    .dash-row { grid-template-columns: 1fr; }
  }
</style>
