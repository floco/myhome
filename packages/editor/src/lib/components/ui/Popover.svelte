<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    open: boolean;
    anchorEl: HTMLElement | null;
    onclose: () => void;
    width?: number;
    children?: Snippet;
  }
  let { open, anchorEl, onclose, width, children }: Props = $props();

  const PANEL_WIDTH = 200;

  let panelEl = $state<HTMLElement | null>(null);
  let panelTop = $state<number | null>(null);
  let panelBottom = $state<number | null>(null);
  let panelLeft = $state(0);

  // Teleport to <body> so position:fixed isn't affected by an ancestor's
  // CSS transform or overflow -- same mechanism as EmojiPicker.svelte's
  // and LayersDropdown.svelte's portal actions.
  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  $effect(() => {
    if (open && anchorEl) {
      const rect = anchorEl.getBoundingClientRect();
      if (rect.top > window.innerHeight / 2) {
        panelBottom = window.innerHeight - rect.top + 4;
        panelTop = null;
      } else {
        panelTop = rect.bottom + 4;
        panelBottom = null;
      }
      panelLeft = Math.max(4, Math.min(rect.left, window.innerWidth - (width ?? PANEL_WIDTH) - 4));
    }
  });

  function handleClickOutside(e: MouseEvent): void {
    if (!open) return;
    const target = e.target as Node;
    if (anchorEl?.contains(target) || panelEl?.contains(target)) return;
    onclose();
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (open && e.key === "Escape") onclose();
  }
</script>

<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown} />

{#if open}
  <div
    class="ui-popover"
    style="left:{panelLeft}px;{width ? `width:${width}px;` : ''}{panelTop !== null ? `top:${panelTop}px;` : ''}{panelBottom !== null ? `bottom:${panelBottom}px;` : ''}"
    bind:this={panelEl}
    use:portal
  >
    {@render children?.()}
  </div>
{/if}

<style>
  .ui-popover {
    position: fixed; z-index: 9999;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    padding: 6px; min-width: 160px;
    display: flex; flex-direction: column; gap: 2px;
    max-height: 60vh; overflow-y: auto;
  }
</style>
