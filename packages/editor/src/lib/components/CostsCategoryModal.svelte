<script lang="ts">
  import type { createCostsStore, YearData } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import StatTile from "./ui/StatTile.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    categoryId: string;
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    onclose: () => void;
    onplaceonmap?: (categoryId: string) => void;
  }

  let { categoryId, costsStore, settingsStore, onclose, onplaceonmap }: Props = $props();

  const category = $derived(settingsStore.costCategories.find(c => c.id === categoryId));
  const hasUnit = $derived((category?.unit ?? null) !== null);
  const byYear = $derived(costsStore.entriesByYear(categoryId));

  const currentYear = new Date().getFullYear();

  const years = $derived((() => {
    const all = [...byYear.keys()].sort();
    return all;
  })());

  const maxAmount = $derived(
    Math.max(...[...byYear.values()].map(d => d.totalAmount), 1)
  );
  const maxQty = $derived(
    hasUnit ? Math.max(...[...byYear.values()].map(d => d.totalQuantity ?? 0), 1) : 1
  );

  const BAR_H = 80;

  function amountBarH(d: YearData): number {
    return Math.round((d.totalAmount / maxAmount) * BAR_H);
  }
  function qtyBarH(d: YearData): number {
    if (!hasUnit || d.totalQuantity == null) return 0;
    return Math.round((d.totalQuantity / maxQty) * BAR_H);
  }

  const completeYears = $derived(years.filter(y => y < currentYear));

  const avgAmount = $derived(
    completeYears.length > 0
      ? completeYears.reduce((a, y) => a + (byYear.get(y)?.totalAmount ?? 0), 0) / completeYears.length
      : 0
  );
  const avgQty = $derived(
    hasUnit && completeYears.length > 0
      ? completeYears.reduce((a, y) => a + (byYear.get(y)?.totalQuantity ?? 0), 0) / completeYears.length
      : null
  );
  const avgUnitPrice = $derived(
    hasUnit && avgQty && avgQty > 0 ? avgAmount / avgQty : null
  );

  function fmt(n: number, dec = 0): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: dec });
  }
</script>

<Modal open={true} title="{category?.emoji ?? ''} {category?.name ?? ''} — per year" {onclose} width="560px">
  {#if years.length === 0}
    <p class="empty">No entries for this category yet.</p>
  {:else}
    <div class="chart-title">
      Cost (€){hasUnit ? ` and volume (${category!.unit})` : ""} per year
    </div>

    <div class="bar-wrap">
      {#each years as y}
        {@const d = byYear.get(y)!}
        {@const isPartial = y === currentYear}
        <div class="bar-group">
          <div class="bars-inner" style="height:{BAR_H}px">
            <div
              class="bar amount-bar"
              class:partial={isPartial}
              style="height:{amountBarH(d)}px;background:{category?.color ?? 'var(--accent)'}"
              title="{y}: {fmt(d.totalAmount)} €"
            ></div>
            {#if hasUnit}
              <div
                class="bar qty-bar"
                class:partial={isPartial}
                style="height:{qtyBarH(d)}px;background:{category?.color ?? 'var(--accent)'}"
                title="{y}: {fmt(d.totalQuantity ?? 0)} {category!.unit}"
              ></div>
            {/if}
          </div>
          <span class="bar-label" class:current={isPartial}>{y}{isPartial ? "*" : ""}</span>
        </div>
      {/each}
    </div>

    <div class="legend">
      <div class="legend-item">
        <span class="swatch" style="background:{category?.color ?? 'var(--accent)'}"></span>
        <span>Cost (€)</span>
      </div>
      {#if hasUnit}
        <div class="legend-item">
          <span class="swatch" style="background:{category?.color ?? 'var(--accent)'};opacity:.5"></span>
          <span>Volume ({category!.unit})</span>
        </div>
      {/if}
      {#if years.some(y => y === currentYear)}
        <span class="partial-note">* current year, partial</span>
      {/if}
    </div>

    <div class="stats">
      <StatTile value="{fmt(avgAmount)} €" label="Avg cost / year" />
      {#if hasUnit && avgQty !== null}
        <StatTile value="{fmt(avgQty, 0)} {category!.unit}" label="Avg {category!.unit} / year" />
        {#if avgUnitPrice !== null}
          <StatTile value="{fmt(avgUnitPrice, 2)} €/{category!.unit}" label="Avg price / {category!.unit}" />
        {/if}
      {/if}
    </div>
  {/if}

  {#snippet footer()}
    {#if onplaceonmap}
      <Button variant="secondary" onclick={() => { onplaceonmap(categoryId); onclose(); }}>📍 Place on map</Button>
    {/if}
    <span class="spacer"></span>
    <Button variant="secondary" onclick={onclose}>Close</Button>
  {/snippet}
</Modal>

<style>
  .empty { color: var(--text-faint); font-size: 13px; text-align: center; padding: 24px 0; }

  .chart-title { font-size: 9px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; }

  .bar-wrap { display: flex; align-items: flex-end; gap: 10px; padding-bottom: 4px; border-bottom: 1px solid var(--border); overflow-x: auto; }
  .bar-group { display: flex; flex-direction: column; align-items: center; gap: 2px; flex-shrink: 0; }
  .bars-inner { display: flex; align-items: flex-end; gap: 2px; }
  .bar { min-width: 14px; border-radius: 2px 2px 0 0; }
  .bar.amount-bar { opacity: .9; }
  .bar.qty-bar { opacity: .5; }
  .bar.partial { outline: 1px dashed currentColor; opacity: .5; }
  .bar-label { font-size: 8px; color: var(--text-faint); white-space: nowrap; }
  .bar-label.current { color: var(--accent); }

  .legend { display: flex; align-items: center; gap: 12px; margin: 8px 0; flex-wrap: wrap; }
  .legend-item { display: flex; align-items: center; gap: 4px; font-size: 9px; color: var(--text-muted); }
  .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }
  .partial-note { font-size: 9px; color: var(--text-faint); margin-left: auto; }

  .stats { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .stats > :global(.ui-stat-tile) { flex: 1; min-width: 120px; padding: 8px 10px; }
  .stats :global(.ui-stat-value) { font-size: 14px; }

  .spacer { flex: 1; }
</style>
