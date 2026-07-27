<!-- packages/editor/src/lib/components/ui/StatTileRow.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children: Snippet;
  }
  let { children }: Props = $props();
</script>

<div class="ui-stat-row">
  {@render children()}
</div>

<style>
  .ui-stat-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--space-3);
  }
</style>
