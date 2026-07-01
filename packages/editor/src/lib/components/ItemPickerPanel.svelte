<script lang="ts">
  export interface PickerItem {
    id: string;
    name: string;
    emoji: string;
    placed: boolean;
  }

  export interface PickerLayer {
    id: string;
    label: string;
    emoji: string;
    items: PickerItem[];
  }

  interface Props {
    layers: PickerLayer[];
    draggingId: string | null;
    highlightId?: string | null;
    ondragstart: (layerId: string, itemId: string, event: DragEvent) => void;
    ondragend: () => void;
  }

  let { layers, draggingId, highlightId = null, ondragstart, ondragend }: Props = $props();

  let query = $state("");
  let openSections = $state<Set<string>>(new Set());

  $effect(() => {
    openSections = layers.length === 1 ? new Set([layers[0].id]) : new Set();
  });

  $effect(() => {
    if (!highlightId) return;
    for (const layer of layers) {
      if (layer.items.some(i => i.id === highlightId)) {
        openSections = new Set([layer.id]);
        break;
      }
    }
    queueMicrotask(() => {
      const el = document.querySelector(`[data-picker-id="${highlightId}"]`);
      if (el) (el as HTMLElement).scrollIntoView({ block: "nearest", behavior: "smooth" });
    });
  });

  function toggleSection(id: string): void {
    const next = new Set(openSections);
    if (next.has(id)) next.delete(id); else next.add(id);
    openSections = next;
  }

  function filteredItems(items: PickerItem[]): PickerItem[] {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(i => i.name.toLowerCase().includes(q) || i.emoji.includes(q));
  }

  function startDrag(layerId: string, item: PickerItem, event: DragEvent): void {
    const el = document.createElement("div");
    el.textContent = item.emoji;
    el.style.cssText = "font-size:28px;position:absolute;top:-100px;pointer-events:none";
    document.body.appendChild(el);
    event.dataTransfer?.setDragImage(el, 14, 14);
    setTimeout(() => document.body.removeChild(el), 0);
    event.dataTransfer?.setData("pickerLayer", layerId);
    event.dataTransfer?.setData("pickerId", item.id);
    ondragstart(layerId, item.id, event);
  }
</script>

<div class="panel">
  <input class="search" placeholder="Search…" bind:value={query} />
  {#each layers as layer (layer.id)}
    {@const filtered = filteredItems(layer.items)}
    {@const unplaced = filtered.filter(i => !i.placed)}
    {@const placed = filtered.filter(i => i.placed)}
    {@const open = openSections.has(layer.id)}
    <div class="section">
      <button class="section-header" onclick={() => toggleSection(layer.id)}>
        <span class="section-icon">{layer.emoji}</span>
        <span class="section-label">{layer.label}</span>
        <span class="section-count">{layer.items.length}</span>
        <span class="chevron">{open ? "▴" : "▾"}</span>
      </button>
      {#if open}
        <div class="section-body">
          {#if unplaced.length > 0}
            <div class="group-title">Unplaced</div>
            {#each unplaced as item (item.id)}
              <div
                class="item-row"
                class:dragging={draggingId === item.id}
                class:highlighted={highlightId === item.id}
                data-picker-id={item.id}
                draggable={true}
                ondragstart={(e) => startDrag(layer.id, item, e)}
                ondragend={() => ondragend()}
                role="button"
                tabindex="0"
              >
                <span class="item-emoji">{item.emoji}</span>
                <span class="item-name">{item.name}</span>
              </div>
            {/each}
          {/if}
          {#if placed.length > 0}
            <div class="group-title">Placed</div>
            {#each placed as item (item.id)}
              <div
                class="item-row placed"
                class:dragging={draggingId === item.id}
                class:highlighted={highlightId === item.id}
                data-picker-id={item.id}
                draggable={true}
                ondragstart={(e) => startDrag(layer.id, item, e)}
                ondragend={() => ondragend()}
                role="button"
                tabindex="0"
              >
                <span class="item-emoji">{item.emoji}</span>
                <span class="item-name">{item.name}</span>
              </div>
            {/each}
          {/if}
          {#if filtered.length === 0}
            <div class="empty">No items match</div>
          {/if}
        </div>
      {/if}
    </div>
  {/each}
</div>

<style>
  .panel {
    width: 220px; height: 100%; background: var(--surface); border-left: 1px solid var(--border);
    display: flex; flex-direction: column; font-size: 12px; color: var(--text-muted);
    flex-shrink: 0; overflow: hidden;
  }
  .search {
    margin: var(--space-2) var(--space-2); padding: var(--space-1) var(--space-2);
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text-muted);
    border-radius: var(--radius-sm); font-size: 11px; flex-shrink: 0;
  }
  .section { border-bottom: 1px solid var(--border); flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
  .section-header {
    width: 100%; display: flex; align-items: center; gap: 6px;
    padding: var(--space-2) var(--space-3); background: var(--surface-alt); border: none; color: var(--text);
    cursor: pointer; font-size: 11px; font-weight: 600; text-align: left;
    flex-shrink: 0;
  }
  .section-header:hover { background: var(--surface-hover); }
  .section-count { margin-left: auto; color: var(--text-faint); font-size: 10px; }
  .chevron { color: var(--text-faint); font-size: 9px; flex-shrink: 0; }
  .section-body { overflow-y: auto; flex: 1; min-height: 0; }
  .group-title {
    color: var(--text-faint); font-size: 9px; text-transform: uppercase;
    letter-spacing: .05em; padding: 4px 10px 2px;
  }
  .item-row {
    display: flex; align-items: center; gap: 8px; padding: 5px 10px;
    cursor: grab; user-select: none; border-radius: var(--radius-sm); margin: 1px 4px;
  }
  .item-row:hover { background: var(--surface-hover); }
  .item-row.placed { opacity: .45; }
  .item-row.dragging { opacity: .5; background: var(--surface-hover); }
  .item-row.highlighted { background: color-mix(in srgb, var(--accent) 18%, transparent); outline: 1px solid var(--accent); opacity: 1; }
  .item-emoji { font-size: 14px; flex-shrink: 0; }
  .item-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .empty { color: var(--text-faint); font-size: 10px; padding: 8px 10px; }
</style>
