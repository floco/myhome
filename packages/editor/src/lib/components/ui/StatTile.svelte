<!-- packages/editor/src/lib/components/ui/StatTile.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    value: string | number;
    label: string;
    variant?: "success" | "danger" | "warning";
    valueContent?: Snippet;
  }
  let { value, label, variant, valueContent }: Props = $props();
</script>

<div class="ui-card ui-stat-tile">
  <div
    class="ui-stat-value"
    class:success={variant === "success"}
    class:danger={variant === "danger"}
    class:warning={variant === "warning"}
  >
    {#if valueContent}{@render valueContent()}{:else}{value}{/if}
  </div>
  <div class="ui-stat-label">{label}</div>
</div>

<style>
  .ui-stat-tile {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-3);
  }
  .ui-stat-value {
    font-family: var(--font-sans);
    font-size: 22px; font-weight: 700; color: var(--text); line-height: 1.2;
  }
  .ui-stat-value.success { color: var(--success); }
  .ui-stat-value.danger { color: var(--danger); }
  .ui-stat-value.warning { color: var(--warning); }
  .ui-stat-label {
    font-family: var(--font-sans);
    font-size: 10px; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: 0.05em;
    margin-top: 2px;
  }
</style>
