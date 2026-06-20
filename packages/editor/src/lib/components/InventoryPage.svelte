<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import InventoryModal from "./InventoryModal.svelte";

  type InvStore = ReturnType<typeof createInventoryStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    store: InvStore;
    floorStore: HouseStore;
    inventoryCategories?: string[];
    selectedItemId?: string | null;
    onclearselection?: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let {
    store,
    floorStore,
    inventoryCategories = [],
    selectedItemId = null,
    onclearselection,
    onplaceonmap,
  }: Props = $props();

  let modalItem = $state<InventoryItem | "create" | null>(null);
  let searchQuery = $state("");
  let roomFilter = $state("");
  let categoryFilter = $state("");

  $effect(() => {
    if (selectedItemId) {
      const found = store.items.find((i) => i.id === selectedItemId);
      if (found) {
        modalItem = found;
        onclearselection?.();
      }
    }
  });

  function roomName(roomId: string | null | undefined): string {
    if (!roomId) return "—";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r: { id: string; label: string }) => r.id === roomId);
      if (room) return room.label || roomId;
    }
    return "—";
  }

  function warrantyChip(item: InventoryItem): { label: string; color: string } {
    if (!item.warrantyExpiryDate) return { label: "—", color: "#445" };
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    const days = Math.round((expiry - now) / 86400000);
    if (days < 0) return { label: "✕ expired", color: "#f44336" };
    if (days <= 30) return { label: `⚠ ${days}d`, color: "#ff9800" };
    return { label: "✓", color: "#4caf50" };
  }

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return d.slice(0, 10);
  }

  function formatPrice(p: number | null): string {
    if (p == null) return "—";
    return p.toLocaleString() + " €";
  }

  const allRooms = $derived(floorStore.floors.flatMap((f: { rooms: { id: string; label: string }[] }) => f.rooms));
  const allCategories = $derived(
    [...new Set(store.items.map((i) => i.category).filter(Boolean))]
  );

  const filtered = $derived(
    store.items.filter((i) => {
      if (
        searchQuery &&
        !i.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
        return false;
      if (roomFilter) {
        if (!i.placement?.roomId) return false;
        if (i.placement.roomId !== roomFilter) return false;
      }
      if (categoryFilter && i.category !== categoryFilter) return false;
      return true;
    })
  );

  const totalValue = $derived(
    store.items.reduce((sum, i) => sum + (i.purchasePrice ?? 0), 0)
  );
</script>

<div class="page">
  <div class="toolbar">
    <input
      class="search"
      bind:value={searchQuery}
      placeholder="🔍 Search items…"
    />
    <select bind:value={roomFilter}>
      <option value="">All rooms</option>
      {#each allRooms as room}
        <option value={room.id}>{room.label}</option>
      {/each}
    </select>
    <select bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each allCategories as cat}
        <option value={cat}>{cat}</option>
      {/each}
    </select>
    <button class="add-btn" onclick={() => { modalItem = "create"; }}>
      ＋ Add item
    </button>
  </div>

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Category</th>
          <th>Room</th>
          <th>Purchased</th>
          <th>Cost</th>
          <th>Warranty</th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as item (item.id)}
          {@const chip = warrantyChip(item)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { modalItem = item; }}>
            <td class="emoji-cell">{item.emoji}</td>
            <td class="name-cell">{item.name}</td>
            <td>{item.category || "—"}</td>
            <td>{roomName(item.placement?.roomId)}</td>
            <td>{formatDate(item.purchaseDate)}</td>
            <td>{formatPrice(item.purchasePrice)}</td>
            <td>
              <span class="chip" style="color:{chip.color}">{chip.label}</span>
            </td>
          </tr>
        {/each}
        {#if filtered.length === 0}
          <tr>
            <td colspan="7" class="empty">
              {store.items.length === 0
                ? "No items yet — click ＋ Add item to get started."
                : "No items match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <div class="footer">
    {store.items.length} item{store.items.length !== 1 ? "s" : ""}
    {#if totalValue > 0}
      · total value: {totalValue.toLocaleString()} €
    {/if}
  </div>
</div>

{#if modalItem}
  <InventoryModal
    item={modalItem === "create" ? null : modalItem}
    {store}
    {inventoryCategories}
    onclose={() => { modalItem = null; }}
    onplaceonmap={onplaceonmap
      ? (id) => { modalItem = null; onplaceonmap!(id); }
      : undefined}
  />
{/if}

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: #141428; font-family: sans-serif;
  }

  .toolbar {
    display: flex; align-items: center; gap: 8px; padding: 8px 12px;
    background: #1e1e3a; border-bottom: 1px solid #2a2a4a; flex-shrink: 0;
  }
  .search {
    flex: 1; background: #111128; border: 1px solid #2a2a4a; color: #ccc;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
  }
  .toolbar select {
    background: #111128; border: 1px solid #2a2a4a; color: #aaa;
    padding: 4px 6px; border-radius: 4px; font-size: 11px;
  }
  .add-btn {
    background: #1a3a2a; border: none; color: #4c9;
    padding: 4px 12px; border-radius: 4px; font-size: 12px;
    cursor: pointer; white-space: nowrap;
  }
  .add-btn:hover { background: #224a34; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: #bbb; }
  thead { position: sticky; top: 0; background: #1a1a30; z-index: 1; }
  th {
    padding: 6px 10px; color: #556; font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid #2a2a3a;
  }
  td { padding: 7px 10px; border-bottom: 1px solid #1e1e2e; }
  tr:hover td { background: #1c1c38; cursor: pointer; }
  .emoji-cell { font-size: 16px; width: 32px; text-align: center; }
  .name-cell { color: #ddd; }
  .chip { font-size: 10px; font-weight: 500; }
  .empty { text-align: center; color: #445; padding: 32px; }

  .footer {
    padding: 6px 12px; font-size: 11px; color: #445;
    border-top: 1px solid #1e1e2e; flex-shrink: 0;
  }
</style>
