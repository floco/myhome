<script lang="ts">
  interface Props {
    activeLayers: Set<string>;
    ontoggle: (layer: string) => void;
  }
  let { activeLayers, ontoggle }: Props = $props();

  let open = $state(false);

  const layers = [
    { id: "chores", icon: "✅", label: "Chores" },
    { id: "inventory", icon: "📦", label: "Inventory" },
    { id: "costs", icon: "💶", label: "Costs" },
    { id: "works", icon: "🔧", label: "Works" },
  ];

  function handleClickOutside(e: MouseEvent) {
    if (!(e.target as HTMLElement).closest(".layers-dropdown")) open = false;
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="layers-dropdown">
  <button
    class="layers-btn"
    class:active={activeLayers.size > 0}
    onclick={() => { open = !open; }}
    title="Toggle map layers"
  >
    Layers <span class="caret">▾</span>
  </button>

  {#if open}
    <div class="dropdown">
      {#each layers as layer}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
        <label class="layer-row" class:checked={activeLayers.has(layer.id)}>
          <input
            type="checkbox"
            checked={activeLayers.has(layer.id)}
            onchange={() => ontoggle(layer.id)}
          />
          <span class="layer-icon">{layer.icon}</span>
          <span>{layer.label}</span>
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

  .dropdown {
    position: absolute; top: calc(100% + 4px); right: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 6px; min-width: 160px;
    z-index: 100; box-shadow: var(--shadow-md);
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
