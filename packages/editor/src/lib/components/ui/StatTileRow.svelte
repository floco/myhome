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
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: var(--space-3);
  }
  .ui-stat-row.column {
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    width: 200px;
  }
  @media (max-width: 700px) {
    .ui-stat-row.column {
      flex-direction: row;
      flex-wrap: wrap;
      width: auto;
    }
    .ui-stat-row.column :global(.ui-stat-tile) {
      flex: 1 1 90px;
    }
  }
</style>
