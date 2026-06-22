<!-- packages/editor/src/lib/components/ui/Badge.svelte -->
<script lang="ts">
  interface Props {
    label: string;
    variant?: "success" | "danger" | "warning" | "neutral";
  }
  let { label, variant = "neutral" }: Props = $props();
</script>

<span class="ui-badge ui-badge-{variant}">{label}</span>

<style>
  .ui-badge {
    font-family: var(--font-sans);
    font-size: 11px; font-weight: 600;
    border-radius: var(--radius-pill);
    padding: 3px 10px;
    white-space: nowrap;
  }
  .ui-badge-neutral { background: var(--surface-alt); color: var(--text-muted); }
  .ui-badge-success { background: color-mix(in srgb, var(--success) 18%, var(--surface)); color: var(--success); }
  .ui-badge-danger { background: color-mix(in srgb, var(--danger) 18%, var(--surface)); color: var(--danger); }
  .ui-badge-warning { background: color-mix(in srgb, var(--warning) 18%, var(--surface)); color: var(--warning); }
</style>
