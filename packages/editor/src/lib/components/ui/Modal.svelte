<!-- packages/editor/src/lib/components/ui/Modal.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    open: boolean;
    title: string;
    onclose: () => void;
    children?: Snippet;
    footer?: Snippet;
  }
  let { open, title, onclose, children, footer }: Props = $props();
</script>

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="ui-modal-backdrop" role="presentation" onclick={onclose}></div>
  <div class="ui-modal" role="dialog" aria-label={title}>
    <div class="ui-modal-header">
      <h2 class="ui-modal-title">{title}</h2>
      <button class="ui-modal-close" onclick={onclose} aria-label="Close">✕</button>
    </div>
    <div class="ui-modal-body">
      {@render children?.()}
    </div>
    {#if footer}
      <div class="ui-modal-footer">
        {@render footer()}
      </div>
    {/if}
  </div>
{/if}

<style>
  .ui-modal-backdrop {
    position: fixed; inset: 0; z-index: 99;
    background: rgba(0, 0, 0, 0.45);
  }
  .ui-modal {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
    z-index: 100;
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    width: 480px; max-width: 90vw; max-height: 90vh;
    display: flex; flex-direction: column;
    overflow: hidden;
  }
  .ui-modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--space-4);
    border-bottom: 1px solid var(--border);
  }
  .ui-modal-title { font-size: 16px; font-weight: 600; color: var(--text); margin: 0; }
  .ui-modal-close {
    border: none; background: transparent; color: var(--text-muted);
    font-size: 14px; cursor: pointer; width: 28px; height: 28px;
    border-radius: var(--radius-sm);
  }
  .ui-modal-close:hover { background: var(--surface-hover); color: var(--text); }
  .ui-modal-body { padding: var(--space-4); overflow-y: auto; flex: 1; }
  .ui-modal-footer {
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--border);
    display: flex; justify-content: flex-end; gap: var(--space-2);
  }
</style>
