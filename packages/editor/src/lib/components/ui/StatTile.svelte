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
  <div class="ui-stat-label">{label}</div>
  <div
    class="ui-stat-value"
    class:success={variant === "success"}
    class:danger={variant === "danger"}
    class:warning={variant === "warning"}
  >
    {#if valueContent}{@render valueContent()}{:else}{value}{/if}
  </div>
</div>

<style>
  .ui-stat-tile {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }
  .ui-stat-label {
    font-family: var(--font-sans);
    font-size: 11px; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: 0.05em;
  }
  .ui-stat-value {
    font-family: var(--font-sans);
    font-size: 28px; font-weight: 700; color: var(--text); line-height: 1.2;
    margin-top: 4px;
  }
  .ui-stat-value.success { color: var(--success); }
  .ui-stat-value.danger { color: var(--danger); }
  .ui-stat-value.warning { color: var(--warning); }
</style>
