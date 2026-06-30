<!-- packages/editor/src/lib/components/ui/Card.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children?: Snippet;
    [key: string]: unknown;
  }
  let { children, ...rest }: Props = $props();
</script>

<div class="ui-card" {...rest}>
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
