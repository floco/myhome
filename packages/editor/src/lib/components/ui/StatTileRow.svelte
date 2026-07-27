<!-- packages/editor/src/lib/components/ui/StatTileRow.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children: Snippet;
    direction?: "row" | "column";
  }
  let { children, direction = "row" }: Props = $props();
</script>

<div class="ui-stat-row" class:column={direction === "column"}>
  {@render children()}
</div>

<style>
  .ui-stat-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--space-3);
  }
  .ui-stat-row.column {
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    width: 200px;
  }
</style>
