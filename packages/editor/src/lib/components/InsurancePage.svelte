<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createInsuranceStore, InsurancePolicy } from "../insuranceStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createContactsStore } from "../contactsStore.svelte";
  import InsuranceModal from "./InsuranceModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";
  import { assignCategoryColors } from "../colorAssignment";

  type InsuranceStore = ReturnType<typeof createInsuranceStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type ContactsStore = ReturnType<typeof createContactsStore>;

  interface Props {
    store: InsuranceStore;
    settingsStore: SettingsStore;
    contactsStore: ContactsStore;
  }

  let { store, settingsStore, contactsStore }: Props = $props();

  let modalPolicy = $state<InsurancePolicy | "create" | null>(null);
  let searchQuery = $state("");
  let categoryFilter = $state("");

  const categoryMap = $derived(
    new Map(settingsStore.insuranceCategories.map(c => [c.id, c]))
  );
  const contactMap = $derived(
    new Map(contactsStore.contacts.map(c => [c.id, c]))
  );

  const FREQUENCY_MULTIPLIER: Record<string, number> = { monthly: 12, quarterly: 4, annual: 1, other: 1 };
  function annualized(p: InsurancePolicy): number {
    return p.premiumAmount != null ? p.premiumAmount * (FREQUENCY_MULTIPLIER[p.premiumFrequency] ?? 1) : 0;
  }

  const filteredPolicies = $derived(store.policies.filter(p => {
    if (categoryFilter && p.categoryId !== categoryFilter) return false;
    if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  }));

  const totalAnnualCost = $derived(store.policies.reduce((sum, p) => sum + annualized(p), 0));

  const categoryBreakdown = $derived((() => {
    const totals = new Map<string, number>();
    for (const p of store.policies) {
      const key = p.categoryId;
      totals.set(key, (totals.get(key) ?? 0) + annualized(p));
    }
    const colors = assignCategoryColors([...totals.keys()]);
    return [...totals.entries()].map(([id, amount]) => {
      const cat = categoryMap.get(id);
      return {
        id, label: cat?.name ?? id, emoji: cat?.emoji ?? "🛡️",
        color: colors.get(id) ?? "var(--chart-series-1)",
        valueLabel: `${fmt(amount)} €`,
        pct: totalAnnualCost > 0 ? (amount / totalAnnualCost) * 100 : 0,
      };
    });
  })());

  function daysUntil(dateStr: string | null): number | null {
    if (!dateStr) return null;
    return Math.round((new Date(dateStr).getTime() - Date.now()) / 86400000);
  }

  function renewalChip(p: InsurancePolicy): { label: string; color: string } | null {
    const days = daysUntil(p.endDate);
    if (days === null) return null;
    if (days < 0) return { label: `✕ ${$_('insurance.page.expired')}`, color: "#f44336" };
    if (days <= 30) return { label: `⚠ ${days}d`, color: "#ff9800" };
    return { label: "✓", color: "#4caf50" };
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
</script>

<div class="page">

  {#if store.policies.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">🛡️</span>
      <p>{$_('insurance.page.emptyCharts')}</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">{$_('insurance.page.byCategory')}</div>
            <DonutChart
              segments={categoryBreakdown}
              centerLabel={$_('insurance.page.annualCost')}
              centerValue={`${fmt(totalAnnualCost)} €`}
              showLabels={true}
            />
          </div>
          <div class="chart-divider"></div>
          <div class="stats-area">
            <div class="chart-label">{$_('chores.page.atAGlance')}</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">{$_('insurance.page.policies')}</div>
                <div class="stat-value">{store.policies.length}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('insurance.page.annualCost')}</div>
                <div class="stat-value">{fmt(totalAnnualCost)} €</div>
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
      <Input placeholder={$_('insurance.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each settingsStore.insuranceCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalPolicy = "create"; }}>＋ {$_('insurance.page.addPolicy')}</Button>
    </div>

    <div class="table-wrapper">
      {#snippet emojiCell(p: InsurancePolicy)}
        {categoryMap.get(p.categoryId)?.emoji ?? "🛡️"}
      {/snippet}
      {#snippet nameCell(p: InsurancePolicy)}
        {p.name}
      {/snippet}
      {#snippet categoryCell(p: InsurancePolicy)}
        {categoryMap.get(p.categoryId)?.name ?? "—"}
      {/snippet}
      {#snippet providerCell(p: InsurancePolicy)}
        {contactMap.get(p.contactId ?? "")?.name ?? "—"}
      {/snippet}
      {#snippet premiumCell(p: InsurancePolicy)}
        {p.premiumAmount != null ? `${fmt(p.premiumAmount)} € / ${$_('insurance.frequency.' + p.premiumFrequency)}` : "—"}
      {/snippet}
      {#snippet endDateCell(p: InsurancePolicy)}
        {p.endDate ?? "—"}
        {#if renewalChip(p)}
          {@const chip = renewalChip(p)}
          <span class="chip" style="color:{chip!.color}">{chip!.label}</span>
        {/if}
      {/snippet}

      <SortableTable
        columns={[
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "name", label: $_('insurance.page.name'), sortValue: (p) => p.name, cellClass: "name-cell", cell: nameCell },
          { key: "category", label: $_('costs.page.category'), sortValue: (p) => categoryMap.get(p.categoryId)?.name ?? null, cell: categoryCell },
          { key: "provider", label: $_('costs.entryModal.supplier'), sortValue: (p) => contactMap.get(p.contactId ?? "")?.name ?? null, cell: providerCell },
          { key: "premium", label: $_('insurance.page.premium'), sortValue: (p) => annualized(p), cell: premiumCell },
          { key: "endDate", label: $_('insurance.page.endDate'), sortValue: (p) => (p.endDate ? new Date(p.endDate) : null), cell: endDateCell },
        ] as Column<InsurancePolicy>[]}
        rows={filteredPolicies}
        rowKey={(p) => p.id}
        rowClick={(p) => { modalPolicy = p; }}
        emptyMessage={store.policies.length === 0 ? $_('insurance.page.emptyNoPolicies') : $_('insurance.page.emptyNoMatch')}
      />
    </div>

    <div class="footer">{$_('insurance.page.footer', { values: { n: filteredPolicies.length } })}</div>
    </Card>
  </div>
</div>

{#if modalPolicy !== null}
  <InsuranceModal
    policy={modalPolicy === "create" ? null : modalPolicy}
    {store}
    {settingsStore}
    {contactsStore}
    onclose={() => { modalPolicy = null; }}
  />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

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
  .filter-sel { cursor: pointer; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  .chip { font-size: 10px; font-weight: 500; margin-left: 6px; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
