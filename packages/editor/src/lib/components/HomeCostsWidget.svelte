<script lang="ts">
  import type { createCostsStore } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    onnavigate: () => void;
  }
  let { costsStore, settingsStore, onnavigate }: Props = $props();

  const breakdown = $derived(costsStore.breakdownLastCompleteYear(settingsStore.costCategories));
  const lastCompleteYearNum = $derived(costsStore.lastCompleteYear());
  const total = $derived(breakdown.reduce((a, b) => a + b.totalAmount, 0));

  const segments = $derived(
    breakdown.map((b) => ({
      id: b.categoryId,
      label: b.name,
      emoji: b.emoji,
      color: b.color,
      valueLabel: `${b.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`,
      pct: b.pct,
    }))
  );
</script>

<div class="widget" role="button" tabindex="0" onclick={onnavigate} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onnavigate(); } }}>
  <Card>
    <div class="header">
      <h3>💶 Costs</h3>
      <span class="sub">{lastCompleteYearNum}</span>
    </div>
    {#if breakdown.length === 0}
      <p class="empty">No cost entries yet.</p>
    {:else}
      <div class="chart-wrap">
        <DonutChart
          {segments}
          centerLabel="Total"
          centerValue={`${total.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`}
        />
      </div>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .sub { font-size: 11px; color: var(--text-faint); }
  .chart-wrap { display: flex; justify-content: center; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
