<script lang="ts">
  import type { createLocationsStore } from "../locationsStore.svelte";
  import { weightedScore } from "../locationsStore.svelte";
  import Card from "./ui/Card.svelte";
  import LocationRankingChart from "./LocationRankingChart.svelte";
  import LocationsMatrix from "./LocationsMatrix.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;
  interface Props { store: LocationsStore; }
  let { store }: Props = $props();

  const ranked = $derived(
    store.locations
      .map((loc) => ({ loc, score: weightedScore(store.criteria, store.ratings, loc.id) }))
      .sort((a, b) => {
        if (a.score === null && b.score === null) return 0;
        if (a.score === null) return 1;
        if (b.score === null) return -1;
        return b.score - a.score;
      }),
  );
  const topScore = $derived(ranked.find((r) => r.score !== null)?.score ?? null);
  const leaders = $derived(topScore === null ? [] : ranked.filter((r) => r.score === topScore));
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
        <div class="chart-inner">
          <div class="stats-area">
            <div class="chart-label">At a glance</div>
            {#if leaders.length === 0}
              <p class="no-leader">No ratings yet</p>
            {:else}
              <div class="leaders-col">
                {#each leaders as { loc, score } (loc.id)}
                  <div class="leader-chip">
                    <span class="crown">👑</span>
                    <span class="leader-emoji">{loc.emoji}</span>
                    <div class="leader-info">
                      <div class="leader-name">{loc.name}</div>
                      <div class="leader-score">{score!.toFixed(1)} / 5</div>
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>

          <div class="chart-divider"></div>

          <div class="bar-area">
            <div class="chart-label">Ranking — weighted overall score</div>
            <LocationRankingChart locations={store.locations} criteria={store.criteria} ratings={store.ratings} />
          </div>
        </div>
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

  .chart-inner { display: flex; gap: 24px; align-items: center; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }
  .bar-area { flex: 2; min-width: 0; }
  .stats-area { flex: 1; min-width: 0; }

  .no-leader { margin: 0; font-size: 12px; color: var(--text-faint); font-style: italic; }
  .leaders-col { display: flex; flex-direction: column; gap: 8px; }
  .leader-chip {
    display: flex; align-items: center; gap: 8px;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .crown { font-size: 14px; }
  .leader-emoji { font-size: 18px; }
  .leader-info { min-width: 0; }
  .leader-name { font-weight: 600; color: var(--text); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .leader-score { font-size: 11px; color: var(--success); font-weight: 600; }
</style>
