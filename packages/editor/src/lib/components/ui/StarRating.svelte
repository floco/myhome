<!-- packages/editor/src/lib/components/ui/StarRating.svelte -->
<script lang="ts">
  interface Props {
    score: number | null;
    size?: "sm" | "md";
    interactive?: boolean;
    onselect?: (score: number) => void;
  }
  let { score, size = "md", interactive = false, onselect }: Props = $props();

  const STAR_VALUES = [1, 2, 3, 4, 5];
</script>

<span class="star-rating star-{size}" class:interactive>
  {#each STAR_VALUES as v (v)}
    {@const filled = score != null && v <= score}
    {#if interactive}
      <button
        type="button"
        class="star-btn"
        class:filled
        onclick={() => onselect?.(v)}
      >{filled ? "★" : "☆"}</button>
    {:else}
      <span class="star" class:filled>{filled ? "★" : "☆"}</span>
    {/if}
  {/each}
</span>

<style>
  .star-rating { display: inline-flex; gap: 1px; line-height: 1; }
  .star-sm { font-size: 12px; }
  .star-md { font-size: 18px; }
  .star { color: var(--text-faint); }
  .star.filled { color: #f5b301; }
  .star-btn {
    border: none; background: none; padding: 0; margin: 0; cursor: pointer;
    font-size: inherit; line-height: 1; color: var(--text-faint);
  }
  .star-btn.filled { color: #f5b301; }
</style>
