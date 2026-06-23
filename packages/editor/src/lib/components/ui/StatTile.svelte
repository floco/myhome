<!-- packages/editor/src/lib/components/ui/StatTile.svelte -->
<script lang="ts">
  interface Props {
    value: string | number;
    label: string;
  }
  let { value, label }: Props = $props();
</script>

<div class="ui-card ui-stat-tile">
  <div class="ui-stat-value">{value}</div>
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
  .ui-stat-label {
    font-family: var(--font-sans);
    font-size: 10px; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: 0.05em;
    margin-top: 2px;
  }
</style>
