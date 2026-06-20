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
    ondragstart: (layerId: string, itemId: string, event: DragEvent) => void;
    ondragend: () => void;
  }

  let { layers, draggingId, ondragstart, ondragend }: Props = $props();

  let query = $state("");
  let openSections = $state<Set<string>>(new Set());

  $effect(() => {
    openSections = layers.length === 1 ? new Set([layers[0].id]) : new Set();
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
    width: 220px; height: 100%; background: #1e1e2e; border-left: 1px solid #333;
    display: flex; flex-direction: column; font-size: 12px; color: #ccc;
    flex-shrink: 0; overflow: hidden;
  }
  .search {
    margin: 6px 8px; padding: 4px 7px; background: #0a0a20;
    border: 1px solid #2a2a4a; color: #bbb; border-radius: 4px;
    font-size: 11px; flex-shrink: 0;
  }
  .section { border-bottom: 1px solid #2a2a3a; flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
  .section-header {
    width: 100%; display: flex; align-items: center; gap: 6px;
    padding: 6px 10px; background: #252535; border: none; color: #aaf;
    cursor: pointer; font-size: 11px; font-weight: 600; text-align: left;
    flex-shrink: 0;
  }
  .section-header:hover { background: #2a2a45; }
  .section-count { margin-left: auto; color: #556; font-size: 10px; }
  .chevron { color: #556; font-size: 9px; flex-shrink: 0; }
  .section-body { overflow-y: auto; flex: 1; min-height: 0; }
  .group-title {
    color: #556; font-size: 9px; text-transform: uppercase;
    letter-spacing: .05em; padding: 4px 10px 2px;
  }
  .item-row {
    display: flex; align-items: center; gap: 8px; padding: 5px 10px;
    cursor: grab; user-select: none; border-radius: 3px; margin: 1px 4px;
  }
  .item-row:hover { background: #2a2a4a; }
  .item-row.placed { opacity: .45; }
  .item-row.dragging { opacity: .5; background: #2a2a4a; }
  .item-emoji { font-size: 14px; flex-shrink: 0; }
  .item-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .empty { color: #445; font-size: 10px; padding: 8px 10px; }
</style>
