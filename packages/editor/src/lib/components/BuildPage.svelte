<!-- packages/editor/src/lib/components/BuildPage.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";
  import Button from "./ui/Button.svelte";
  import PhaseSection from "./PhaseSection.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import StatTileRow from "./ui/StatTileRow.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    store: BuildStore;
    onopentask: (taskId: string) => void;
  }
  let { store, onopentask }: Props = $props();

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
  <div class="page">
    <div class="stat-row-wrap">
      <StatTileRow>
        <StatTile
          label={$_('build.dashboard.status')}
          value={$_(`build.projectStatus.${store.project.status === "in_progress" ? "inProgress" : store.project.status === "on_hold" ? "onHold" : store.project.status}`)}
        />
        <StatTile
          label={$_('build.dashboard.currentPhase')}
          value={currentPhase ? resolveLabel(currentPhase.nameKey, currentPhase.nameOverride) : "—"}
        />
        <StatTile label={$_('build.dashboard.percentComplete')} value={`${Math.round(store.projectProgress * 100)}%`} />
        <StatTile label={$_('build.dashboard.plannedBudget')} value={fmtMoney(store.projectBudget.planned)} />
        <StatTile label={$_('build.dashboard.actualCost')} value={fmtMoney(store.projectBudget.actual)} />
      </StatTileRow>
    </div>

    <div class="table-card-wrap">
      <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
        <PhaseSection {store} {onopentask} />
      </Card>
    </div>
  </div>
{/if}

<style>
  .start-card { display: flex; justify-content: center; padding: var(--space-4); }
  .start-card :global(.ui-card) { max-width: 480px; text-align: center; }
  .start-error { color: var(--danger); font-size: 12px; margin: 8px 0; }

  .page { display: flex; flex-direction: column; height: 100%; }

  .stat-row-wrap { padding: var(--space-4); flex-shrink: 0; }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }
</style>
