<!-- packages/editor/src/lib/components/ui/Card.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children?: Snippet;
  }
  let { children }: Props = $props();
</script>

<div class="ui-card">
  {@render children?.()}
</div>

<style>
  .ui-card {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-4);
  }
</style>
