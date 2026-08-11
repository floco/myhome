<script lang="ts">
  import { _ } from "svelte-i18n";

  interface Props {
    activeLayers: Set<string>;
    ontoggle: (layer: string) => void;
    popoverAlign?: 'left' | 'right';
    /** 'pill' (default) is the standalone dashboard-widget look; 'toolbar'
     *  matches the floor-plan editor's icon-over-label .ft-btn buttons
     *  (Picker, Furniture) for visual consistency in that toolbar. */
    variant?: 'pill' | 'toolbar';
  }
  let { activeLayers, ontoggle, popoverAlign = 'left', variant = 'pill' }: Props = $props();

  let open = $state(false);
  let wrapper = $state<HTMLElement | null>(null);
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let panelEl = $state<HTMLElement | null>(null);
  let panelTop = $state<number | null>(null);
  let panelBottom = $state<number | null>(null);
  let panelLeft = $state<number | null>(null);
  let panelRight = $state<number | null>(null);

  const layers = [
    { id: "chores",      icon: "✅" },
    { id: "inventory",   icon: "📦" },
    { id: "consumables", icon: "🛒" },
    { id: "costs",       icon: "💰" },
    { id: "works",       icon: "🔧" },
    { id: "ha",          icon: "📡" },
  ];

  // Teleport the panel to <body> so position:fixed isn't clipped by an
  // ancestor with overflow set (e.g. the mobile floating-toolbar's
  // overflow-x:auto) -- same mechanism as EmojiPicker.svelte's portal action.
  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  function toggleOpen(): void {
    if (!open && triggerEl) {
      const rect = triggerEl.getBoundingClientRect();
      if (rect.top > window.innerHeight / 2) {
        panelBottom = window.innerHeight - rect.top + 4;
        panelTop = null;
      } else {
        panelTop = rect.bottom + 4;
        panelBottom = null;
      }
      // Clamp so the panel (min-width 160) can't run off either edge of a
      // narrow mobile viewport.
      if (popoverAlign === 'right') {
        panelLeft = Math.max(4, Math.min(rect.left, window.innerWidth - 168));
        panelRight = null;
      } else {
        panelLeft = null;
        panelRight = Math.max(4, Math.min(window.innerWidth - rect.right, window.innerWidth - 168));
      }
    }
    open = !open;
  }

  function handleClickOutside(e: MouseEvent) {
    const target = e.target as Node;
    if (wrapper?.contains(target) || panelEl?.contains(target)) return;
    open = false;
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="layers-dropdown" bind:this={wrapper}>
  <button
    class="layers-btn"
    class:toolbar={variant === 'toolbar'}
    class:active={activeLayers.size > 0}
    bind:this={triggerEl}
    onclick={toggleOpen}
    title={$_('floorPlan.layers.toggle')}
  >
    {#if variant === 'toolbar'}
      🗂️ <span class="ft-label">{$_('floorPlan.layers.title')}</span>
    {:else}
      {$_('floorPlan.layers.title')} <span class="caret">▾</span>
    {/if}
  </button>

  {#if open}
    <div
      class="dropdown"
      style="{panelTop !== null ? `top:${panelTop}px;` : ''}{panelBottom !== null ? `bottom:${panelBottom}px;` : ''}{panelLeft !== null ? `left:${panelLeft}px;` : ''}{panelRight !== null ? `right:${panelRight}px;` : ''}"
      bind:this={panelEl}
      use:portal
    >
      {#each layers as layer}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
        <label class="layer-row" class:checked={activeLayers.has(layer.id)}>
          <input
            type="checkbox"
            checked={activeLayers.has(layer.id)}
            onchange={() => ontoggle(layer.id)}
          />
          <span class="layer-icon">{layer.icon}</span>
          <span>{$_(`common.modules.${layer.id}`)}</span>
        </label>
      {/each}
    </div>
  {/if}
</div>

<style>
  .layers-dropdown { position: relative; }

  .layers-btn {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text-muted);
    padding: 3px 10px; border-radius: var(--radius-sm); font-size: 11px;
    cursor: pointer; display: flex; align-items: center; gap: 5px;
    white-space: nowrap; height: 26px;
  }
  .layers-btn:hover { background: var(--surface-hover); }
  .layers-btn.active { border-color: var(--accent); color: var(--text); }
  .caret { font-size: 9px; }

  /* 'toolbar' variant mirrors App.svelte's .ft-btn styling so this button
     reads as part of the same icon-over-label group as Picker/Furniture. */
  .layers-btn.toolbar {
    width: 100%; height: 28px;
    background: transparent; border: none; border-radius: var(--radius-sm);
    color: var(--text-muted); font-size: 13px; padding: 0 6px;
    justify-content: flex-start;
  }
  .layers-btn.toolbar:hover { background: var(--surface-hover); color: var(--text); }
  .layers-btn.toolbar.active { background: var(--surface-hover); border-color: transparent; color: var(--accent); }
  .layers-btn.toolbar .ft-label { font-size: 11px; font-weight: 500; }

  @media (max-width: 480px) { /* --bp-mobile */
    .layers-btn.toolbar { width: auto; flex-direction: column; gap: 1px; font-size: 10px; height: auto; }
    .layers-btn.toolbar .ft-label { display: none; }
  }

  .dropdown {
    position: fixed;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 6px; min-width: 160px;
    z-index: 9999; box-shadow: var(--shadow-md);
  }

  .layer-row {
    display: flex; align-items: center; gap: 8px;
    padding: 5px 8px; border-radius: var(--radius-sm); cursor: pointer;
    color: var(--text-muted); font-size: 12px;
  }
  .layer-row:hover { background: var(--surface-hover); }
  .layer-row.checked { color: var(--text); }
  .layer-row input { accent-color: var(--accent); cursor: pointer; }
  .layer-icon { font-size: 14px; width: 18px; text-align: center; }
</style>
