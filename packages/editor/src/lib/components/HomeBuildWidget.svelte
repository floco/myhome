<!-- packages/editor/src/lib/components/HomeBuildWidget.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    buildStore: BuildStore;
    onnavigate: () => void;
  }
  let { buildStore, onnavigate }: Props = $props();

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " €";
  }

  const overdueCount = $derived(
    buildStore.tasks.filter((t) => t.status !== "completed" && t.plannedDueDate && t.plannedDueDate < new Date().toISOString().slice(0, 10)).length
  );
</script>

{#if buildStore.project}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div class="widget" role="button" tabindex="0" onclick={onnavigate} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onnavigate(); } }}>
    <Card>
      <div class="header"><h3>🏗️ {$_('common.modules.build')}</h3></div>
      <div class="stat-row">
        <span class="stat">{$_(`build.projectStatus.${buildStore.project.status === "in_progress" ? "inProgress" : buildStore.project.status === "on_hold" ? "onHold" : buildStore.project.status}`)}</span>
        <span class="stat">{Math.round(buildStore.projectProgress * 100)}%</span>
      </div>
      <div class="budget-row">
        <span>{fmt(buildStore.projectBudget.planned)}</span>
        <span class="sep">/</span>
        <span>{fmt(buildStore.projectBudget.actual)}</span>
      </div>
      {#if overdueCount > 0}
        <div class="overdue">{overdueCount} {$_('build.dashboard.overdueTasks')}</div>
      {/if}
    </Card>
  </div>
{/if}

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .stat-row { display: flex; gap: 10px; font-size: 12px; font-weight: 600; margin-bottom: 4px; }
  .budget-row { font-size: 12px; color: var(--text-muted); }
  .sep { margin: 0 4px; }
  .overdue { margin-top: 4px; font-size: 11px; color: var(--danger); }
</style>
