<!-- packages/editor/src/lib/components/ui/Panel.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    density?: "normal" | "compact";
    children?: Snippet;
  }
  let { density = "normal", children }: Props = $props();
</script>

<div class="ui-panel ui-panel-{density}">
  {@render children?.()}
</div>

<style>
  .ui-panel {
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .ui-panel-normal { border-radius: var(--radius-lg); padding: var(--space-4); }
  .ui-panel-compact { border-radius: var(--radius-sm); padding: var(--space-2); font-size: 12px; }
</style>
