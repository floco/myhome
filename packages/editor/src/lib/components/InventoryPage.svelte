<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import InventoryModal from "./InventoryModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";

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
    <Input bind:value={searchQuery} placeholder="🔍 Search items…" />
    <select class="native-input" bind:value={roomFilter}>
      <option value="">All rooms</option>
      {#each allRooms as room}
        <option value={room.id}>{room.label}</option>
      {/each}
    </select>
    <select class="native-input" bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each allCategories as cat}
        <option value={cat}>{cat}</option>
      {/each}
    </select>
    <Button onclick={() => { modalItem = "create"; }}>＋ Add item</Button>
  </div>

  <div class="table-wrapper">
    {#snippet emojiCell(item: InventoryItem)}
      {item.emoji}
    {/snippet}
    {#snippet nameCell(item: InventoryItem)}
      {item.name}
    {/snippet}
    {#snippet categoryCell(item: InventoryItem)}
      {item.category || "—"}
    {/snippet}
    {#snippet roomCell(item: InventoryItem)}
      {roomName(item.placement?.roomId)}
    {/snippet}
    {#snippet purchasedCell(item: InventoryItem)}
      {formatDate(item.purchaseDate)}
    {/snippet}
    {#snippet costCell(item: InventoryItem)}
      {formatPrice(item.purchasePrice)}
    {/snippet}
    {#snippet warrantyCell(item: InventoryItem)}
      {@const chip = warrantyChip(item)}
      <span class="chip" style="color:{chip.color}">{chip.label}</span>
    {/snippet}

    <SortableTable
      columns={[
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "name", label: "Name", sortValue: (i) => i.name, cellClass: "name-cell", cell: nameCell },
        { key: "category", label: "Category", sortValue: (i) => i.category || null, cell: categoryCell },
        { key: "room", label: "Room", sortValue: (i) => roomName(i.placement?.roomId), cell: roomCell },
        { key: "purchased", label: "Purchased", sortValue: (i) => (i.purchaseDate ? new Date(i.purchaseDate) : null), cell: purchasedCell },
        { key: "cost", label: "Cost", sortValue: (i) => i.purchasePrice, cell: costCell },
        { key: "warranty", label: "Warranty", sortable: false, cell: warrantyCell },
      ] as Column<InventoryItem>[]}
      rows={filtered}
      rowKey={(item) => item.id}
      rowClick={(item) => { modalItem = item; }}
      emptyMessage={store.items.length === 0
        ? "No items yet — click ＋ Add item to get started."
        : "No items match your filters."}
    />
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
    background: var(--bg); font-family: var(--font-sans);
  }

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); }
  .chip { font-size: 10px; font-weight: 500; }

  .footer {
    padding: 6px 12px; font-size: 11px; color: var(--text-faint);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
</style>
