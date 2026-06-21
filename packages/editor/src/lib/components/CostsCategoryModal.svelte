<!-- packages/editor/src/lib/components/CostsCategoryModal.svelte -->
<script lang="ts">
  import type { createCostsStore, YearData } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";

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

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="overlay" onclick={(e) => { if (e.target === e.currentTarget) onclose(); }}>
  <div class="modal">
    <div class="modal-header">
      <h2>{category?.emoji ?? ""} {category?.name ?? ""} — per year</h2>
      <button class="close-btn" onclick={onclose}>✕</button>
    </div>

    <div class="modal-body">
      {#if years.length === 0}
        <p class="empty">No entries for this category yet.</p>
      {:else}
        <div class="chart-title">
          Cost (€){hasUnit ? ` and volume (${category!.unit})` : ""} per year
        </div>

        <!-- Bar chart -->
        <div class="bar-wrap">
          {#each years as y}
            {@const d = byYear.get(y)!}
            {@const isPartial = y === currentYear}
            <div class="bar-group">
              <div class="bars-inner" style="height:{BAR_H}px">
                <div
                  class="bar amount-bar"
                  class:partial={isPartial}
                  style="height:{amountBarH(d)}px;background:{category?.color ?? '#4466cc'}"
                  title="{y}: {fmt(d.totalAmount)} €"
                ></div>
                {#if hasUnit}
                  <div
                    class="bar qty-bar"
                    class:partial={isPartial}
                    style="height:{qtyBarH(d)}px;background:{category?.color ?? '#4466cc'}"
                    title="{y}: {fmt(d.totalQuantity ?? 0)} {category!.unit}"
                  ></div>
                {/if}
              </div>
              <span class="bar-label" class:current={isPartial}>{y}{isPartial ? "*" : ""}</span>
            </div>
          {/each}
        </div>

        <!-- Legend -->
        <div class="legend">
          <div class="legend-item">
            <span class="swatch" style="background:{category?.color ?? '#4466cc'}"></span>
            <span>Cost (€)</span>
          </div>
          {#if hasUnit}
            <div class="legend-item">
              <span class="swatch" style="background:{category?.color ?? '#4466cc'};opacity:.5"></span>
              <span>Volume ({category!.unit})</span>
            </div>
          {/if}
          {#if years.some(y => y === currentYear)}
            <span class="partial-note">* current year, partial</span>
          {/if}
        </div>

        <!-- Stat chips -->
        <div class="stats">
          <div class="stat">
            <div class="stat-title">Avg cost / year</div>
            <div class="stat-value">{fmt(avgAmount)} €</div>
          </div>
          {#if hasUnit && avgQty !== null}
            <div class="stat">
              <div class="stat-title">Avg {category!.unit} / year</div>
              <div class="stat-value">{fmt(avgQty, 0)} {category!.unit}</div>
            </div>
            {#if avgUnitPrice !== null}
              <div class="stat">
                <div class="stat-title">Avg price / {category!.unit}</div>
                <div class="stat-value">{fmt(avgUnitPrice, 2)} €/{category!.unit}</div>
              </div>
            {/if}
          {/if}
        </div>
      {/if}
    </div>

    <div class="modal-footer">
      {#if onplaceonmap}
        <button class="place-btn" onclick={() => { onplaceonmap!(categoryId); onclose(); }}>📍 Place on map</button>
      {/if}
      <span class="spacer"></span>
      <button onclick={onclose}>Close</button>
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed; inset: 0; z-index: 200;
    background: rgba(0,0,0,.6);
    display: flex; align-items: center; justify-content: center;
  }
  .modal {
    background: #1a1a30; border: 1px solid #3a3a5a; border-radius: 10px;
    width: 560px; max-width: 95vw; max-height: 90vh;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 8px 32px #0008;
  }
  .modal-header {
    display: flex; align-items: center; padding: 14px 18px;
    border-bottom: 1px solid #2a2a4a; flex-shrink: 0;
  }
  h2 { margin: 0; font-size: 15px; color: #eee; font-family: sans-serif; font-weight: 600; flex: 1; }
  .close-btn { background: none; border: none; color: #667; font-size: 16px; cursor: pointer; }
  .close-btn:hover { color: #aaa; }

  .modal-body { padding: 16px 18px; overflow-y: auto; flex: 1; font-family: sans-serif; }
  .empty { color: #445; font-size: 13px; text-align: center; padding: 24px 0; }

  .chart-title { font-size: 9px; color: #556; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; }

  .bar-wrap { display: flex; align-items: flex-end; gap: 10px; padding-bottom: 4px; border-bottom: 1px solid #1e1e2e; overflow-x: auto; }
  .bar-group { display: flex; flex-direction: column; align-items: center; gap: 2px; flex-shrink: 0; }
  .bars-inner { display: flex; align-items: flex-end; gap: 2px; }
  .bar { min-width: 14px; border-radius: 2px 2px 0 0; }
  .bar.amount-bar { opacity: .9; }
  .bar.qty-bar { opacity: .5; }
  .bar.partial { outline: 1px dashed currentColor; opacity: .5; }
  .bar-label { font-size: 8px; color: #445; white-space: nowrap; }
  .bar-label.current { color: #88aaff; }

  .legend { display: flex; align-items: center; gap: 12px; margin: 8px 0; flex-wrap: wrap; }
  .legend-item { display: flex; align-items: center; gap: 4px; font-size: 9px; color: #778; }
  .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }
  .partial-note { font-size: 9px; color: #445; margin-left: auto; }

  .stats { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .stat {
    flex: 1; min-width: 120px; background: #111128; border: 1px solid #2a2a4a;
    border-radius: 4px; padding: 8px 10px;
  }
  .stat-title { font-size: 8px; color: #445; text-transform: uppercase; margin-bottom: 3px; }
  .stat-value { font-size: 14px; color: #eee; font-weight: 600; }

  .modal-footer {
    display: flex; align-items: center; gap: 8px; padding: 12px 18px;
    border-top: 1px solid #2a2a4a; flex-shrink: 0; font-family: sans-serif;
  }
  .spacer { flex: 1; }
  button { padding: 5px 14px; border-radius: 4px; font-size: 12px; cursor: pointer; background: none; border: 1px solid #2a2a4a; color: #778; }
  button:hover { background: #1e1e3a; color: #ccc; }
  .place-btn { background: #1e2a4a; border-color: #3a4a8a; color: #aac; }
  .place-btn:hover { background: #2a3a6a; color: #ccf; }
</style>
