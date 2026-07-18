<script lang="ts">
  import type { createLocationsStore } from "../locationsStore.svelte";
  import Card from "./ui/Card.svelte";
  import LocationRankingChart from "./LocationRankingChart.svelte";
  import LocationsMatrix from "./LocationsMatrix.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;
  interface Props { store: LocationsStore; }
  let { store }: Props = $props();
</script>

<div class="page">
  {#if store.locations.length === 0}
    <div class="empty-state">
      <span class="empty-icon">🌍</span>
      <p>No locations yet — add candidates below to start comparing.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">Ranking — weighted overall score</div>
        <LocationRankingChart locations={store.locations} criteria={store.criteria} ratings={store.ratings} />
      </Card>
    </div>
  {/if}

  <div class="matrix-card-wrap">
    <Card style="padding:0; overflow:hidden;">
      <LocationsMatrix {store} />
    </Card>
  </div>
</div>

<style>
  .page {
    display: flex; flex-direction: column; height: 100%; background: var(--bg);
    font-family: var(--font-sans); gap: var(--space-4); padding: var(--space-4);
    box-sizing: border-box; overflow-y: auto;
  }
  .empty-state {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint);
  }
  .empty-icon { font-size: 36px; }
  .empty-state p { margin: 0; font-size: 13px; }
  .chart-card-wrap { flex-shrink: 0; }
  .chart-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; }
  .matrix-card-wrap { flex: 1; min-height: 0; }
</style>
