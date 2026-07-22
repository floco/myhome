<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createLocationsStore } from "../locationsStore.svelte";
  import { weightedScore } from "../locationsStore.svelte";
  import Card from "./ui/Card.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;

  interface Props {
    locationsStore: LocationsStore;
    onnavigate: () => void;
  }
  let { locationsStore, onnavigate }: Props = $props();

  const ranked = $derived(
    locationsStore.locations
      .map((loc) => ({ loc, score: weightedScore(locationsStore.criteria, locationsStore.ratings, loc.id) }))
      .sort((a, b) => (b.score ?? -1) - (a.score ?? -1)),
  );
  const top = $derived(ranked[0] ?? null);
  const rest = $derived(ranked.slice(1, 4));
</script>

{#if locationsStore.locations.length > 0}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div
    class="widget"
    role="button"
    tabindex="0"
    onclick={onnavigate}
    onkeydown={(e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onnavigate();
      }
    }}
  >
    <Card>
      <div class="header"><h3>🌍 {$_('common.modules.locations')}</h3></div>
      {#if top}
        <div class="top-pick">
          <span class="crown">👑</span>
          <span class="emoji">{top.loc.emoji}</span>
          <span class="name">{top.loc.name}</span>
          <span class="score">{top.score !== null ? top.score.toFixed(1) : "—"}</span>
        </div>
      {/if}
      {#if rest.length > 0}
        <ul class="rest-list">
          {#each rest as { loc, score } (loc.id)}
            <li>
              <span class="emoji">{loc.emoji}</span>
              <span class="name">{loc.name}</span>
              <span class="score">{score !== null ? score.toFixed(1) : "—"}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </Card>
  </div>
{/if}

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .top-pick { display: flex; align-items: center; gap: 6px; font-size: 13px; margin-bottom: 6px; }
  .top-pick .name { font-weight: 700; color: var(--text); flex: 1; }
  .top-pick .score { font-weight: 600; color: var(--success); }
  .rest-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .rest-list li { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-muted); }
  .rest-list .name { flex: 1; }
  .rest-list .score { font-weight: 600; }
</style>
