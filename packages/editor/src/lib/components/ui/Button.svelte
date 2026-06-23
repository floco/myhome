<!-- packages/editor/src/lib/components/ui/Button.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "primary" | "secondary" | "ghost";
    onclick?: () => void;
    disabled?: boolean;
    title?: string;
    children?: Snippet;
  }
  let { variant = "primary", onclick, disabled = false, title, children }: Props = $props();
</script>

<button type="button" class="ui-button ui-button-{variant}" {disabled} {title} {onclick}>
  {@render children?.()}
</button>

<style>
  .ui-button {
    font-family: var(--font-sans);
    font-size: 12px; font-weight: 600;
    border: none; border-radius: var(--radius-pill);
    padding: 8px 18px; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  }
  .ui-button:disabled { opacity: 0.5; cursor: default; }

  .ui-button-primary { background: var(--accent); color: var(--accent-contrast); }
  .ui-button-primary:hover:not(:disabled) { opacity: 0.85; }

  .ui-button-secondary {
    background: var(--surface); color: var(--text);
    border: 1px solid var(--border);
  }
  .ui-button-secondary:hover:not(:disabled) { background: var(--surface-hover); }

  .ui-button-ghost { background: transparent; color: var(--text-muted); }
  .ui-button-ghost:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
</style>
