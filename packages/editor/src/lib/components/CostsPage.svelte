<!-- packages/editor/src/lib/components/CostsPage.svelte -->
<script lang="ts">
  import type { createCostsStore, CostEntry, CategoryBreakdown } from "../costsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createHouseStore } from "../houseStore.svelte";
  import CostsEntryModal from "./CostsEntryModal.svelte";
  import CostsCategoryModal from "./CostsCategoryModal.svelte";

  type CostsStore = ReturnType<typeof createCostsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type HouseStore = ReturnType<typeof createHouseStore>;

  interface Props {
    costsStore: CostsStore;
    settingsStore: SettingsStore;
    floorStore: HouseStore;
    onplaceonmap?: (catId: string) => void;
  }

  let { costsStore, settingsStore, floorStore, onplaceonmap }: Props = $props();

  let modalEntry = $state<CostEntry | "create" | null>(null);
  let chartModalCategoryId = $state<string | null>(null);
  let searchQuery = $state("");
  let categoryFilter = $state("");
  let yearFilter = $state("");

  const categoryMap = $derived(
    new Map(settingsStore.costCategories.map(c => [c.id, c]))
  );
  const supplierMap = $derived(
    new Map(settingsStore.suppliers.map(s => [s.id, s]))
  );

  function categoryName(categoryId: string): string {
    return categoryMap.get(categoryId)?.name ?? "Unknown";
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
        const sup = (e.supplierId ? (supplierMap.get(e.supplierId)?.name ?? "") : "").toLowerCase();
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

  // --- Chart helpers ---

  interface Slice {
    cat: CategoryBreakdown;
    startDeg: number;
    endDeg: number;
    midDeg: number;
  }

  function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = angleDeg * Math.PI / 180;
    return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) };
  }

  function donutPath(cx: number, cy: number, outerR: number, innerR: number, startDeg: number, endDeg: number): string {
    const clampedEnd = Math.min(startDeg + 359.99, endDeg);
    const os = polarPoint(cx, cy, outerR, startDeg);
    const oe = polarPoint(cx, cy, outerR, clampedEnd);
    const is = polarPoint(cx, cy, innerR, startDeg);
    const ie = polarPoint(cx, cy, innerR, clampedEnd);
    const large = (clampedEnd - startDeg) > 180 ? 1 : 0;
    return [
      `M ${os.x.toFixed(2)} ${os.y.toFixed(2)}`,
      `A ${outerR} ${outerR} 0 ${large} 1 ${oe.x.toFixed(2)} ${oe.y.toFixed(2)}`,
      `L ${ie.x.toFixed(2)} ${ie.y.toFixed(2)}`,
      `A ${innerR} ${innerR} 0 ${large} 0 ${is.x.toFixed(2)} ${is.y.toFixed(2)}`,
      "Z",
    ].join(" ");
  }

  const PIE_CX = 155;
  const PIE_CY = 110;
  const PIE_OUTER_R = 70;
  const PIE_INNER_R = 28;

  const breakdown = $derived(costsStore.breakdownLastCompleteYear(settingsStore.costCategories));
  const yearlyTotals = $derived(costsStore.totalByYear());
  const lastCompleteYearNum = $derived(costsStore.lastCompleteYear());

  const slices = $derived((() => {
    let angle = 0;
    return breakdown.map(cat => {
      const start = angle;
      const span = (cat.pct / 100) * 360;
      angle += span;
      return { cat, startDeg: start, endDeg: angle, midDeg: start + span / 2 } as Slice;
    });
  })());

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
      <span class="empty-icon">💶</span>
      <p>No entries yet — click ＋ Add entry to get started.</p>
    </div>
  {:else}
    <div class="chart-section">
      <div class="chart-inner">

        <!-- Pie chart with connector labels -->
        <div class="pie-area">
          <div class="chart-label">
            {lastCompleteYearNum} — breakdown by category
          </div>
          <svg
            viewBox="0 0 310 220"
            width="310"
            height="220"
            style="overflow:visible"
          >
            <!-- Slices -->
            {#each slices as s (s.cat.categoryId)}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <path
                d={donutPath(PIE_CX, PIE_CY, PIE_OUTER_R, PIE_INNER_R, s.startDeg, s.endDeg)}
                fill={s.cat.color}
                opacity="0.9"
                style="cursor:pointer"
                onclick={() => { chartModalCategoryId = s.cat.categoryId; }}
              />
            {/each}

            <!-- Donut hole -->
            <circle cx={PIE_CX} cy={PIE_CY} r={PIE_INNER_R} fill="#141428" />
            <text x={PIE_CX} y={PIE_CY - 6} text-anchor="middle" fill="#778" font-size="8" font-family="sans-serif">Total</text>
            <text x={PIE_CX} y={PIE_CY + 8} text-anchor="middle" fill="#ddd" font-size="11" font-family="sans-serif" font-weight="600">
              {breakdown.reduce((a, b) => a + b.totalAmount, 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} €
            </text>

            <!-- Connector lines + labels -->
            {#each slices as s (s.cat.categoryId + "-label")}
              {@const mid = polarPoint(PIE_CX, PIE_CY, PIE_OUTER_R + 4, s.midDeg)}
              {@const elbow = polarPoint(PIE_CX, PIE_CY, PIE_OUTER_R + 18, s.midDeg)}
              {@const isRight = elbow.x >= PIE_CX}
              {@const lineEnd = { x: elbow.x + (isRight ? 28 : -28), y: elbow.y }}
              {@const textX = lineEnd.x + (isRight ? 4 : -4)}
              <line x1={mid.x} y1={mid.y} x2={elbow.x} y2={elbow.y} stroke={s.cat.color} stroke-width="1" opacity="0.7" />
              <line x1={elbow.x} y1={elbow.y} x2={lineEnd.x} y2={lineEnd.y} stroke={s.cat.color} stroke-width="1" opacity="0.7" />
              <circle cx={mid.x} cy={mid.y} r="2" fill={s.cat.color} />
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <text
                x={textX}
                y={elbow.y - 3}
                text-anchor={isRight ? "start" : "end"}
                fill={s.cat.color}
                font-size="9"
                font-family="sans-serif"
                font-weight="600"
                style="cursor:pointer"
                onclick={() => { chartModalCategoryId = s.cat.categoryId; }}
              >{s.cat.emoji} {s.cat.name}</text>
              <text
                x={textX}
                y={elbow.y + 9}
                text-anchor={isRight ? "start" : "end"}
                fill="#99a"
                font-size="8"
                font-family="sans-serif"
              >{s.cat.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })} € · {s.cat.pct.toFixed(0)}%</text>
            {/each}
          </svg>
        </div>

        <div class="chart-divider"></div>

        <!-- 10-year total bar chart -->
        <div class="bar-area">
          <div class="chart-label">Total house costs — last 10 years (€)</div>
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
          <div class="stat-chips">
            <div class="stat-chip">
              <div class="stat-title">10-year avg</div>
              <div class="stat-value">{tenYearAvg.toLocaleString(undefined, { maximumFractionDigits: 0 })} €/yr</div>
            </div>
            <div class="stat-chip">
              <div class="stat-title">Last complete yr</div>
              <div class="stat-value">
                {lastCompleteTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €
                {#if yoyPct !== null}
                  <span class="yoy" class:up={yoyPct > 0} class:down={yoyPct < 0}>
                    {yoyPct > 0 ? "▲" : "▼"}{Math.abs(yoyPct)}%
                  </span>
                {/if}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  {/if}

  <!-- Toolbar -->
  <div class="toolbar">
    <input class="search" bind:value={searchQuery} placeholder="🔍 Search entries…" />
    <select bind:value={categoryFilter}>
      <option value="">All categories</option>
      {#each settingsStore.costCategories as cat}
        <option value={cat.id}>{cat.emoji} {cat.name}</option>
      {/each}
    </select>
    <select bind:value={yearFilter}>
      <option value="">All years</option>
      {#each allYears as y}
        <option value={String(y)}>{y}</option>
      {/each}
    </select>
    <button class="add-btn" onclick={() => { modalEntry = "create"; }}>＋ Add entry</button>
  </div>

  <!-- Table -->
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Category</th>
          <th>Date</th>
          <th>Supplier</th>
          <th class="num-col">Qty</th>
          <th class="num-col">Unit price</th>
          <th class="num-col">Total</th>
          <th>Room</th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as entry (entry.id)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
          <tr onclick={() => { modalEntry = entry; }}>
            <td class="emoji-cell">{categoryEmoji(entry.categoryId)}</td>
            <td class="name-cell">{categoryName(entry.categoryId)}</td>
            <td>{entry.date}</td>
            <td>{entry.supplierId ? (supplierMap.get(entry.supplierId)?.name ?? "—") : "—"}</td>
            <td class="num-col">{formatQty(entry)}</td>
            <td class="num-col">{formatUnitPrice(entry)}</td>
            <td class="num-col amount-cell">{entry.totalAmount.toLocaleString()} €</td>
            <td>{roomName(entry.roomId)}</td>
          </tr>
        {/each}
        {#if filtered.length === 0}
          <tr>
            <td colspan="8" class="empty">
              {costsStore.entries.length === 0
                ? "No entries yet — click ＋ Add entry to get started."
                : "No entries match your filters."}
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <div class="footer">
    {filtered.length} entr{filtered.length !== 1 ? "ies" : "y"}
    {#if filteredTotal > 0}
      · total: {filteredTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })} €
    {/if}
  </div>
</div>

{#if modalEntry}
  <CostsEntryModal
    entry={modalEntry === "create" ? null : modalEntry}
    {costsStore}
    {settingsStore}
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
    background: #141428; font-family: sans-serif;
  }

  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: #445; border-bottom: 1px solid #1e1e2e; flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-section {
    padding: 0; border-bottom: 1px solid #1e1e2e; flex-shrink: 0;
  }
  .chart-inner {
    display: flex; gap: 24px; align-items: flex-start; padding: 12px 16px;
    background: #141428;
  }
  .chart-label {
    font-size: 10px; color: #556; text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .pie-area { flex-shrink: 0; }
  .chart-divider { width: 1px; background: #2a2a4a; align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .bar-area { flex: 1; min-width: 0; }
  .bar-chart-wrap { display: flex; align-items: flex-end; gap: 4px; height: 120px; }
  .y-axis {
    display: flex; flex-direction: column; justify-content: space-between;
    align-items: flex-end; height: 100px; padding-bottom: 16px;
    font-size: 8px; color: #334; flex-shrink: 0; padding-right: 4px;
  }
  .bars { display: flex; align-items: flex-end; gap: 4px; flex: 1; height: 100%; padding-bottom: 16px; border-bottom: 1px solid #1e1e2e; border-left: 1px solid #1e1e2e; }
  .bar-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1; height: 100%; gap: 2px; }
  .bar { width: 100%; border-radius: 2px 2px 0 0; background: #2a3a6a; min-height: 2px; transition: height .2s; }
  .bar.highlight { background: #4466cc; }
  .bar.partial { background: #2a3a5a; outline: 1px dashed #4466cc; opacity: .6; }
  .bar.empty { background: transparent; }
  .bar-label { font-size: 7px; color: #445; white-space: nowrap; }
  .bar-label.current-label { color: #88aaff; }

  .stat-chips { display: flex; gap: 8px; margin-top: 8px; }
  .stat-chip {
    flex: 1; background: #111128; border: 1px solid #2a2a4a;
    border-radius: 4px; padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: #445; text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: #eee; font-weight: 600; }
  .yoy { font-size: 10px; margin-left: 4px; }
  .yoy.up { color: #f97; }
  .yoy.down { color: #4c9; }

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
    text-transform: uppercase; letter-spacing: .05em;
    text-align: left; border-bottom: 1px solid #2a2a3a;
  }
  th.num-col { text-align: right; }
  td { padding: 7px 10px; border-bottom: 1px solid #1e1e2e; }
  td.num-col { text-align: right; }
  tr:hover td { background: #1c1c38; cursor: pointer; }
  .emoji-cell { font-size: 15px; width: 28px; text-align: center; }
  .name-cell { color: #ddd; }
  .amount-cell { color: #eee; }
  .empty { text-align: center; color: #445; padding: 32px; }

  .footer {
    padding: 6px 12px; font-size: 11px; color: #445;
    border-top: 1px solid #1e1e2e; flex-shrink: 0;
  }
</style>
