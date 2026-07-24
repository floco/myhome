<!-- packages/editor/src/lib/components/BuildPage.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore } from "../buildStore.svelte";
  import Card from "./ui/Card.svelte";
  import Button from "./ui/Button.svelte";
  import PhaseSection from "./PhaseSection.svelte";

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
      <div class="stat-row">
        <Card>
          <div class="stat-title">{$_('build.dashboard.status')}</div>
          <div class="stat-value">{$_(`build.projectStatus.${store.project.status === "in_progress" ? "inProgress" : store.project.status === "on_hold" ? "onHold" : store.project.status}`)}</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.currentPhase')}</div>
          <div class="stat-value">{currentPhase ? resolveLabel(currentPhase.nameKey, currentPhase.nameOverride) : "—"}</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.percentComplete')}</div>
          <div class="stat-value">{Math.round(store.projectProgress * 100)}%</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.plannedBudget')}</div>
          <div class="stat-value">{fmtMoney(store.projectBudget.planned)}</div>
        </Card>
        <Card>
          <div class="stat-title">{$_('build.dashboard.actualCost')}</div>
          <div class="stat-value">{fmtMoney(store.projectBudget.actual)}</div>
        </Card>
      </div>
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
  .stat-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-3); }
  .stat-title { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .stat-value { font-size: 18px; font-weight: 700; color: var(--text); }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 900px) {
    .stat-row { grid-template-columns: repeat(2, 1fr); }
  }
</style>
