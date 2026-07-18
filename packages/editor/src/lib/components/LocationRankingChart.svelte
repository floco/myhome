<script lang="ts">
  import type { Location, LocationCriterion, LocationRating } from "../locationsStore.svelte";
  import { weightedScore } from "../locationsStore.svelte";

  interface Props {
    locations: Location[];
    criteria: LocationCriterion[];
    ratings: LocationRating[];
  }
  let { locations, criteria, ratings }: Props = $props();

  const ranked = $derived(
    locations
      .map((loc) => ({ loc, score: weightedScore(criteria, ratings, loc.id) }))
      .sort((a, b) => {
        if (a.score === null && b.score === null) return 0;
        if (a.score === null) return 1;
        if (b.score === null) return -1;
        return b.score - a.score;
      }),
  );

  const topScore = $derived(ranked.find((r) => r.score !== null)?.score ?? null);

  function isWinner(score: number | null): boolean {
    return score !== null && topScore !== null && score === topScore;
  }
</script>

<div class="ranking">
  {#each ranked as { loc, score } (loc.id)}
    <div class="row">
      <div class="label">
        {#if isWinner(score)}<span class="crown">👑</span>{/if}
        <span class="emoji">{loc.emoji}</span>
        <span class="name">{loc.name}</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:{score !== null ? (score / 5) * 100 : 0}%"></div>
      </div>
      <div class="score">{score !== null ? score.toFixed(1) : "—"}</div>
    </div>
  {/each}
</div>

<style>
  .ranking { display: flex; flex-direction: column; gap: 8px; }
  .row { display: flex; align-items: center; gap: 10px; }
  .label { display: flex; align-items: center; gap: 4px; width: 160px; flex-shrink: 0; font-size: 12px; color: var(--text); }
  .crown { font-size: 12px; }
  .emoji { font-size: 14px; }
  .name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar-track { flex: 1; height: 10px; background: var(--surface-alt); border-radius: 5px; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--accent); border-radius: 5px; transition: width 0.2s; }
  .score { width: 32px; text-align: right; font-size: 12px; font-weight: 600; color: var(--text-muted); flex-shrink: 0; }
</style>
