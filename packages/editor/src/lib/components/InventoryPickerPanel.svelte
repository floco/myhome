<script lang="ts">
  import type { InventoryItem } from "../inventoryStore.svelte";

  interface Props {
    items: InventoryItem[];
    currentFloorId: string;
    draggingItemId: string | null;
    onDragStart: (itemId: string) => void;
    onDragEnd: () => void;
  }

  let { items, currentFloorId, draggingItemId, onDragStart, onDragEnd }: Props =
    $props();

  let query = $state("");

  const placed = $derived(
    items.filter((i) => i.placement?.floorId === currentFloorId)
  );
  const allUnplaced = $derived(items.filter((i) => i.placement === null));
  const unplaced = $derived(
    query
      ? allUnplaced.filter((i) =>
          i.name.toLowerCase().includes(query.toLowerCase())
        )
      : allUnplaced
  );
</script>

<div class="panel">
  <div class="panel-header">
    📦 Inventory <span class="hint">— drag to floor</span>
  </div>
  <input class="search" bind:value={query} placeholder="Search…" />

  {#if placed.length > 0}
    <div class="section">
      <div class="section-title">On this floor ({placed.length})</div>
      {#each placed as item (item.id)}
        <div class="item-row placed">
          <span class="emoji">{item.emoji}</span>
          <span class="name">{item.name}</span>
          <span class="pin-icon">📍</span>
        </div>
      {/each}
    </div>
  {/if}

  <div class="section unplaced-section">
    <div class="section-title">
      Unplaced ({allUnplaced.length})
    </div>
    {#each unplaced as item (item.id)}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="item-row"
        class:dragging={draggingItemId === item.id}
        draggable={true}
        ondragstart={(e) => {
          e.dataTransfer?.setData("inventoryItemId", item.id);
          onDragStart(item.id);
        }}
        ondragend={() => onDragEnd()}
      >
        <span class="emoji">{item.emoji}</span>
        <span class="name">{item.name}</span>
      </div>
    {/each}
    {#if unplaced.length === 0 && query}
      <div class="empty">No matches</div>
    {:else if allUnplaced.length === 0}
      <div class="empty">All items placed ✓</div>
    {/if}
  </div>
</div>

<style>
  .panel {
    background: #111130; border-left: 1px solid #2a2a4a;
    display: flex; flex-direction: column; width: 220px; flex-shrink: 0;
    font-family: sans-serif; font-size: 12px; overflow: hidden; height: 100%;
  }
  .panel-header {
    padding: 8px 10px; border-bottom: 1px solid #2a2a3a;
    color: #aaf; font-size: 11px; font-weight: 600; flex-shrink: 0;
  }
  .hint { color: #556; font-weight: normal; font-size: 10px; }
  .search {
    margin: 6px 8px; padding: 4px 7px;
    background: #0a0a20; border: 1px solid #2a2a4a; color: #bbb;
    border-radius: 4px; font-size: 11px; flex-shrink: 0;
  }
  .section { overflow-y: auto; padding: 4px; }
  .unplaced-section { flex: 1; }
  .section-title {
    color: #556; font-size: 9px; text-transform: uppercase;
    letter-spacing: .05em; padding: 2px 4px;
  }
  .item-row {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 6px; border-radius: 4px; cursor: grab; color: #ccc;
  }
  .item-row:hover { background: #1c1c38; }
  .item-row.placed { opacity: .45; cursor: default; }
  .item-row.dragging { opacity: .5; background: #1c1c38; }
  .emoji { font-size: 14px; width: 18px; text-align: center; flex-shrink: 0; }
  .name {
    flex: 1; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; font-size: 11px;
  }
  .pin-icon { font-size: 10px; color: #445; }
  .empty { color: #445; font-size: 10px; padding: 4px 6px; }
</style>
