<script lang="ts">
  import type { createInventoryStore, InventoryItem } from "../inventoryStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import InventoryModal from "./InventoryModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";
  import { assignCategoryColors } from "../colorAssignment";

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

  interface CategoryCount {
    category: string;
    count: number;
  }

  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of store.items) {
      const key = item.category || "Uncategorized";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());

  const categoryColors = $derived(assignCategoryColors(categoryCounts.map((c) => c.category)));

  const categoryBreakdown = $derived(
    categoryCounts.map((c) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: categoryColors.get(c.category) ?? "var(--chart-series-1)",
      valueLabel: `${c.count}`,
      pct: store.items.length > 0 ? (c.count / store.items.length) * 100 : 0,
    }))
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

  {#if store.items.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">📦</span>
      <p>No items yet — click ＋ Add item to get started.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">By category</div>
            <DonutChart
              segments={categoryBreakdown}
              centerLabel="Items"
              centerValue={`${store.items.length}`}
              showLabels={true}
            />
          </div>

          <div class="chart-divider"></div>

          <div class="stats-area">
            <div class="chart-label">At a glance</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">Items</div>
                <div class="stat-value">{store.items.length}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">Total value</div>
                <div class="stat-value">{totalValue.toLocaleString()} €</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
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
    </Card>
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

  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-inner { display: flex; gap: 24px; align-items: center; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .pie-area { flex-shrink: 0; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .stats-area { flex: 1; min-width: 0; }
  .stat-chips-col { display: flex; flex-direction: column; gap: 8px; max-width: 220px; }
  .stat-chip {
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

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
