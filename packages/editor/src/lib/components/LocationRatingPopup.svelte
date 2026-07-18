<script lang="ts">
  import type { Location, LocationCriterion, LocationRating } from "../locationsStore.svelte";

  interface Props {
    location: Location;
    criterion: LocationCriterion;
    rating: LocationRating | null;
    anchorX: number;
    anchorY: number;
    onsave: (score: number | null, note: string) => void;
    onclose: () => void;
  }
  let { location, criterion, rating, anchorX, anchorY, onsave, onclose }: Props = $props();

  let score = $state<number | null>(rating?.score ?? null);
  let note = $state(rating?.note ?? "");

  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  function selectScore(v: number): void {
    score = score === v ? null : v;
  }

  function handleSave(): void {
    onsave(score, note);
  }

  function handleClear(): void {
    onsave(null, "");
  }

  function handleWindowKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window onkeydown={handleWindowKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="popup-backdrop" role="presentation" onclick={onclose} use:portal></div>
<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="popup" style="left:{anchorX}px;top:{anchorY}px" onclick={(e) => e.stopPropagation()} use:portal>
  <div class="popup-title">{location.emoji} {location.name} — {criterion.name}</div>
  <div class="score-picker">
    {#each [1, 2, 3, 4, 5] as v}
      <button type="button" class="score-btn" class:selected={score === v} onclick={() => selectScore(v)}>{v}</button>
    {/each}
  </div>
  <textarea class="note-textarea" placeholder="Note…" bind:value={note}></textarea>
  <div class="popup-actions">
    <button type="button" class="save-btn" onclick={handleSave}>Save</button>
    <button type="button" class="clear-btn" onclick={handleClear}>Clear</button>
    <button type="button" class="close-btn" onclick={onclose}>Close</button>
  </div>
</div>

<style>
  .popup-backdrop { position: fixed; inset: 0; z-index: 998; background: transparent; }
  .popup {
    position: fixed; z-index: 999;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    padding: 12px; width: 240px;
  }
  .popup-title { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
  .score-picker { display: flex; gap: 4px; margin-bottom: 8px; }
  .score-btn {
    flex: 1; padding: 6px 0; border: 1px solid var(--border); background: var(--surface-alt);
    color: var(--text-muted); border-radius: var(--radius-sm); cursor: pointer; font-size: 12px; font-weight: 600;
  }
  .score-btn.selected { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); }
  .note-textarea {
    width: 100%; min-height: 50px; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); padding: 6px 8px; font-size: 12px;
    font-family: var(--font-sans); box-sizing: border-box; resize: vertical; margin-bottom: 8px;
  }
  .popup-actions { display: flex; gap: 6px; }
  .save-btn {
    flex: 1; background: var(--accent); color: var(--accent-contrast); border: none;
    border-radius: var(--radius-sm); padding: 6px 0; cursor: pointer; font-size: 12px; font-weight: 600;
  }
  .clear-btn, .close-btn {
    background: var(--surface-alt); color: var(--text-muted); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px; cursor: pointer; font-size: 12px;
  }
</style>
