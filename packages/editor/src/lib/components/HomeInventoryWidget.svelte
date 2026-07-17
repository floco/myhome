<script lang="ts">
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";
  import { assignCategoryColors } from "../colorAssignment";

  type InventoryStore = ReturnType<typeof createInventoryStore>;

  interface Props {
    inventoryStore: InventoryStore;
    onnavigate: () => void;
  }
  let { inventoryStore, onnavigate }: Props = $props();

  interface CategoryCount {
    category: string;
    count: number;
  }

  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of inventoryStore.items) {
      const key = item.category || "Uncategorized";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());

  const total = $derived(categoryCounts.reduce((a, c) => a + c.count, 0));

  const categoryColors = $derived(assignCategoryColors(categoryCounts.map((c) => c.category)));

  const segments = $derived(
    categoryCounts.map((c) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: categoryColors.get(c.category) ?? "var(--chart-series-1)",
      valueLabel: `${c.count}`,
      pct: total > 0 ? (c.count / total) * 100 : 0,
    }))
  );
</script>

<div class="widget" role="button" tabindex="0" onclick={onnavigate} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onnavigate(); } }}>
  <Card>
    <div class="header">
      <h3>📦 Inventory</h3>
      <span class="sub">{total} items</span>
    </div>
    {#if categoryCounts.length === 0}
      <p class="empty">No inventory items yet.</p>
    {:else}
      <div class="chart-wrap">
        <DonutChart {segments} centerLabel="Items" centerValue={`${total}`} showLabels compact />
      </div>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .sub { font-size: 11px; color: var(--text-faint); }
  .chart-wrap { display: flex; justify-content: center; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
