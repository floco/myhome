<script lang="ts">
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";

  type InventoryStore = ReturnType<typeof createInventoryStore>;

  interface Props {
    inventoryStore: InventoryStore;
    onnavigate: () => void;
  }
  let { inventoryStore, onnavigate }: Props = $props();

  const PALETTE = ["#5b8def", "#f2994a", "#27ae60", "#eb5757", "#9b51e0", "#17a2b8", "#f2c94c", "#bdbdbd"];

  function paletteFor(str: string): string {
    let h = 0;
    for (const ch of str) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }

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

  const segments = $derived(
    categoryCounts.map((c) => ({
      id: c.category,
      label: c.category,
      emoji: "📦",
      color: paletteFor(c.category),
      valueLabel: `${c.count}`,
      pct: total > 0 ? (c.count / total) * 100 : 0,
    }))
  );

  function colorFor(category: string): string {
    return paletteFor(category);
  }
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
      <div class="body">
        <div class="chart-wrap">
          <DonutChart {segments} centerLabel="Items" centerValue={`${total}`} />
        </div>
        <ul class="counts">
          {#each categoryCounts as c (c.category)}
            <li>
              <span class="dot" style="background:{colorFor(c.category)}"></span>
              {c.category} <b>{c.count}</b>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  </Card>
</div>

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .sub { font-size: 11px; color: var(--text-faint); }
  .body { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
  .chart-wrap { display: flex; justify-content: center; }
  .counts { list-style: none; margin: 0; padding: 0; width: 100%; font-size: 12px; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
  .counts li { display: flex; align-items: center; gap: 6px; }
  .counts b { margin-left: auto; color: var(--text); }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: var(--space-4) 0; margin: 0; }
</style>
