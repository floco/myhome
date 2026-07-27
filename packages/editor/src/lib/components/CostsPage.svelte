<!-- packages/editor/src/lib/components/CostsPage.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createCostsStore, CostEntry } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createContactsStore } from "../contactsStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import CostsEntryModal from "./CostsEntryModal.svelte";
  import CostsCategoryModal from "./CostsCategoryModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import DonutChart from "./DonutChart.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type ContactsStore = ReturnType<typeof createContactsStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    contactsStore: ContactsStore;
    floorStore: HouseStore;
    onplaceonmap?: (catId: string) => void;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }

  let { costsStore, settingsStore, contactsStore, floorStore, onplaceonmap, selectedItemId = null, onclearselection }: Props = $props();

  let modalEntry = $state<CostEntry | "create" | null>(null);

  $effect(() => {
    if (selectedItemId) {
      const found = costsStore.entries.find((e) => e.id === selectedItemId);
      if (found) {
        modalEntry = found;
        onclearselection?.();
      }
    }
  });

  let chartModalCategoryId = $state<string | null>(null);
  let searchQuery = $state("");
  let categoryFilter = $state("");
  let yearFilter = $state("");

  const categoryMap = $derived(
    new Map(settingsStore.costCategories.map(c => [c.id, c]))
  );
  const supplierMap = $derived(
    new Map(contactsStore.contacts.map(c => [c.id, c]))
  );

  function categoryName(categoryId: string): string {
    return categoryMap.get(categoryId)?.name ?? $_('costs.page.unknown');
  }

  function categoryEmoji(categoryId: string): string {
    return categoryMap.get(categoryId)?.emoji ?? "?";
  }

  function categoryUnit(categoryId: string): string | null {
    return categoryMap.get(categoryId)?.unit ?? null;
  }

  function roomName(roomId: string | null | undefined): string {
    if (!roomId) return "—";
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r: { id: string; label: string }) => r.id === roomId);
      if (room) return room.label || roomId;
    }
    return "—";
  }

  function formatQty(entry: CostEntry): string {
    if (entry.quantity == null) return "—";
    const unit = categoryUnit(entry.categoryId);
    return unit ? `${entry.quantity.toLocaleString()} ${unit}` : String(entry.quantity);
  }

  function formatUnitPrice(entry: CostEntry): string {
    if (entry.unitPrice == null) return "—";
    const unit = categoryUnit(entry.categoryId);
    return unit ? `${entry.unitPrice} €/${unit}` : `${entry.unitPrice} €`;
  }

  const allYears = $derived(
    [...new Set(costsStore.entries.map(e => new Date(e.date).getFullYear()))].sort((a, b) => b - a)
  );

  const filtered = $derived(
    costsStore.entries.filter(e => {
      if (categoryFilter && e.categoryId !== categoryFilter) return false;
      if (yearFilter && new Date(e.date).getFullYear() !== parseInt(yearFilter)) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const name = categoryName(e.categoryId).toLowerCase();
        const sup = (e.contactId ? (supplierMap.get(e.contactId)?.name ?? "") : "").toLowerCase();
        const notes = e.notes.toLowerCase();
        if (!name.includes(q) && !sup.includes(q) && !notes.includes(q)) return false;
      }
      return true;
    }).sort((a, b) => b.date.localeCompare(a.date))
  );

  const filteredTotal = $derived(
    filtered.reduce((sum, e) => sum + e.totalAmount, 0)
  );

  const hasEntries = $derived(costsStore.entries.length > 0);

  const breakdown = $derived(costsStore.breakdownLastCompleteYear(settingsStore.costCategories));
  const yearlyTotals = $derived(costsStore.totalByYear());
  const lastCompleteYearNum = $derived(costsStore.lastCompleteYear());

  const currentYear = new Date().getFullYear();
  const chartYears = $derived((() => {
    const years: number[] = [];
    const from = currentYear - 9;
    for (let y = from; y <= currentYear; y++) years.push(y);
    return years;
  })());

  const maxBarAmount = $derived(
    Math.max(...chartYears.map(y => yearlyTotals.get(y) ?? 0), 1)
  );

  function barHeight(year: number, maxPx: number): number {
    const amt = yearlyTotals.get(year) ?? 0;
    return Math.round((amt / maxBarAmount) * maxPx);
  }

  function formatK(n: number): string {
    return n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(Math.round(n));
  }

  const tenYearAvg = $derived((() => {
    const completeYears = chartYears.filter(y => y < currentYear && (yearlyTotals.get(y) ?? 0) > 0);
    if (completeYears.length === 0) return 0;
    const sum = completeYears.reduce((a, y) => a + (yearlyTotals.get(y) ?? 0), 0);
    return sum / completeYears.length;
  })());

  const lastCompleteTotal = $derived(yearlyTotals.get(lastCompleteYearNum) ?? 0);
  const prevYearTotal = $derived(yearlyTotals.get(lastCompleteYearNum - 1) ?? 0);
  const yoyPct = $derived(
    prevYearTotal > 0 ? Math.round(((lastCompleteTotal - prevYearTotal) / prevYearTotal) * 100) : null
  );
</script>

<div class="page">

  <!-- Chart section -->
  {#if !hasEntries}
    <div class="empty-charts">
      <span class="empty-icon">💰</span>
      <p>{$_('costs.page.emptyCharts')}</p>
    </div>
  {:else}
    {#snippet lastCompleteYearValue()}
      {lastCompleteTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €
      {#if yoyPct !== null}
        <span class="yoy" class:up={yoyPct > 0} class:down={yoyPct < 0}>
          {yoyPct > 0 ? "▲" : "▼"}{Math.abs(yoyPct)}%
        </span>
      {/if}
    {/snippet}

    <div class="chart-card-wrap">
      <!-- Pie chart with connector labels -- spans both grid rows -->
      <Card>
        <div class="chart-label">
          {$_('costs.page.breakdownByCategory', { values: { year: lastCompleteYearNum } })}
        </div>
        <DonutChart
          segments={breakdown.map((b) => ({
            id: b.categoryId,
            label: b.name,
            emoji: b.emoji,
            color: b.color,
            valueLabel: `${b.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`,
            pct: b.pct,
          }))}
          centerLabel={$_('costs.page.total')}
          centerValue={`${breakdown.reduce((a, b) => a + b.totalAmount, 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} €`}
          showLabels={true}
          insideLabels={true}
          onsliceclick={(id) => { chartModalCategoryId = id; }}
        />
      </Card>

      <!-- 10-year total bar chart -->
      <Card>
        <div class="chart-label">{$_('costs.page.totalHouseCosts')}</div>
        <div class="bar-chart-wrap">
          <div class="y-axis">
            <span>{formatK(maxBarAmount)}</span>
            <span>{formatK(Math.round(maxBarAmount / 2))}</span>
            <span>0</span>
          </div>
          <div class="bars">
            {#each chartYears as y}
              {@const h = barHeight(y, 100)}
              {@const isLastComplete = y === lastCompleteYearNum}
              {@const isCurrent = y === currentYear}
              {@const hasData = (yearlyTotals.get(y) ?? 0) > 0}
              <div class="bar-col">
                <div
                  class="bar"
                  class:highlight={isLastComplete}
                  class:partial={isCurrent}
                  class:empty={!hasData}
                  style="height:{h}px"
                  title="{y}: {(yearlyTotals.get(y) ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} €"
                ></div>
                <span class="bar-label" class:current-label={isCurrent}>{y}</span>
              </div>
            {/each}
          </div>
        </div>
      </Card>

      <!-- The two stats, side by side, under the bar chart -->
      <div class="stats-under-bar">
        <StatTile
          label={$_('costs.page.tenYearAvg')}
          value={$_('costs.page.perYear', { values: { amount: tenYearAvg.toLocaleString(undefined, { maximumFractionDigits: 0 }) } })}
        />
        <StatTile
          label={$_('costs.page.lastCompleteYr')}
          value={`${lastCompleteTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €`}
          valueContent={lastCompleteYearValue}
        />
      </div>
    </div>
  {/if}

  <!-- Table -->
  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <!-- Toolbar -->
    <div class="toolbar">
      <Input bind:value={searchQuery} placeholder={$_('costs.page.searchEntries')} />
      <select class="native-input" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each settingsStore.costCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={yearFilter}>
        <option value="">{$_('costs.page.allYears')}</option>
        {#each allYears as y}
          <option value={String(y)}>{y}</option>
        {/each}
      </select>
      <Button onclick={() => { modalEntry = "create"; }}>＋ {$_('costs.page.addEntry')}</Button>
    </div>

    <div class="table-wrapper">
    {#snippet emojiCell(entry: CostEntry)}
      {categoryEmoji(entry.categoryId)}
    {/snippet}
    {#snippet categoryCell(entry: CostEntry)}
      {categoryName(entry.categoryId)}
    {/snippet}
    {#snippet dateCell(entry: CostEntry)}
      {entry.date}
    {/snippet}
    {#snippet supplierCell(entry: CostEntry)}
      {entry.contactId ? (supplierMap.get(entry.contactId)?.name ?? "—") : "—"}
    {/snippet}
    {#snippet qtyCell(entry: CostEntry)}
      {formatQty(entry)}
    {/snippet}
    {#snippet unitPriceCell(entry: CostEntry)}
      {formatUnitPrice(entry)}
    {/snippet}
    {#snippet totalCell(entry: CostEntry)}
      {entry.totalAmount.toLocaleString()} €
    {/snippet}
    {#snippet roomCell(entry: CostEntry)}
      {roomName(entry.roomId)}
    {/snippet}

    <SortableTable
      columns={[
        { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
        { key: "category", label: $_('costs.page.category'), sortValue: (e) => categoryName(e.categoryId), cellClass: "name-cell", cell: categoryCell },
        { key: "date", label: $_('costs.page.date'), sortValue: (e) => new Date(e.date), cell: dateCell },
        { key: "supplier", label: $_('costs.page.supplier'), sortValue: (e) => (e.contactId ? supplierMap.get(e.contactId)?.name ?? null : null), cell: supplierCell },
        { key: "qty", label: $_('costs.page.qty'), headerClass: "num-col", cellClass: "num-col", sortValue: (e) => e.quantity, cell: qtyCell },
        { key: "unitPrice", label: $_('costs.page.unitPrice'), headerClass: "num-col", cellClass: "num-col", sortValue: (e) => e.unitPrice, cell: unitPriceCell },
        { key: "total", label: $_('costs.page.total'), headerClass: "num-col", cellClass: "num-col amount-cell", sortValue: (e) => e.totalAmount, cell: totalCell },
        { key: "room", label: $_('costs.page.room'), sortValue: (e) => roomName(e.roomId), cell: roomCell },
      ] as Column<CostEntry>[]}
      rows={filtered}
      rowKey={(entry) => entry.id}
      rowClick={(entry) => { modalEntry = entry; }}
      emptyMessage={costsStore.entries.length === 0
        ? $_('costs.page.emptyNoEntries')
        : $_('costs.page.emptyNoMatch')}
    />
    </div>

    <div class="footer">
      {$_('costs.page.entryCount', { values: { n: filtered.length } })}
      {#if filteredTotal > 0}
        {$_('costs.page.totalSuffix', { values: { amount: filteredTotal.toLocaleString(undefined, { maximumFractionDigits: 0 }) } })}
      {/if}
    </div>
    </Card>
  </div>
</div>

{#if modalEntry}
  <CostsEntryModal
    entry={modalEntry === "create" ? null : modalEntry}
    {costsStore}
    {settingsStore}
    {contactsStore}
    {floorStore}
    onclose={() => { modalEntry = null; }}
  />
{/if}

{#if chartModalCategoryId}
  <CostsCategoryModal
    categoryId={chartModalCategoryId}
    {costsStore}
    {settingsStore}
    onclose={() => { chartModalCategoryId = null; }}
    {onplaceonmap}
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

  .chart-card-wrap {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    gap: var(--space-3);
    padding: var(--space-4);
    flex-shrink: 0;
  }
  .chart-card-wrap > :global(.ui-card:nth-child(1)) { grid-column: 1; grid-row: 1 / 3; }
  .chart-card-wrap > :global(.ui-card:nth-child(2)) { grid-column: 2; grid-row: 1; min-width: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .stats-under-bar { grid-column: 2; grid-row: 2; display: flex; gap: var(--space-3); }
  .stats-under-bar > :global(.ui-card) { flex: 1; min-width: 0; }

  .bar-chart-wrap { display: flex; align-items: flex-end; gap: 4px; height: 120px; }
  .y-axis {
    display: flex; flex-direction: column; justify-content: space-between;
    align-items: flex-end; height: 100px; padding-bottom: 16px;
    font-size: 8px; color: var(--text-faint); flex-shrink: 0; padding-right: 4px;
  }
  .bars { display: flex; align-items: flex-end; gap: 4px; flex: 1; height: 100%; padding-bottom: 16px; border-bottom: 1px solid var(--border); border-left: 1px solid var(--border); }
  .bar-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1; height: 100%; gap: 2px; }
  .bar { width: 100%; border-radius: 2px 2px 0 0; background: color-mix(in srgb, var(--accent) 35%, var(--surface)); min-height: 2px; transition: height .2s; }
  .bar.highlight { background: var(--accent); }
  .bar.partial { background: var(--surface-alt); outline: 1px dashed var(--accent); opacity: .8; }
  .bar.empty { background: transparent; }
  .bar-label { font-size: 7px; color: var(--text-faint); white-space: nowrap; }
  .bar-label.current-label { color: var(--accent); }

  .yoy { font-size: 10px; margin-left: 4px; }
  .yoy.up { color: var(--danger); }
  .yoy.down { color: var(--success); }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 900px) {
    .chart-card-wrap { grid-template-columns: 1fr; grid-template-rows: auto auto auto; }
    .chart-card-wrap > :global(.ui-card:nth-child(1)) { grid-column: 1; grid-row: 1; }
    .chart-card-wrap > :global(.ui-card:nth-child(2)) { grid-column: 1; grid-row: 2; }
    .stats-under-bar { grid-column: 1; grid-row: 3; }
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
  :global(.num-col) { text-align: right; }
  :global(.emoji-cell) { font-size: 15px; width: 28px; text-align: center; }
  :global(.name-cell) { color: var(--text); }
  :global(.amount-cell) { color: var(--text); }

  .footer {
    padding: 6px 12px; font-size: 11px; color: var(--text-faint);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
</style>
