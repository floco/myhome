<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createPropertiesStore, Property } from "../propertiesStore.svelte";
  import type { createLocationsStore } from "../locationsStore.svelte";
  import PropertyModal from "./PropertyModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import StatTileRow from "./ui/StatTileRow.svelte";
  import Modal from "./ui/Modal.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
  import AttachmentIcon from "./ui/AttachmentIcon.svelte";

  type PropertiesStore = ReturnType<typeof createPropertiesStore>;
  type LocationsStore = ReturnType<typeof createLocationsStore>;

  interface Props {
    store: PropertiesStore;
    locationsStore: LocationsStore;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }

  let { store, locationsStore, selectedItemId = null, onclearselection }: Props = $props();

  let modalProperty = $state<Property | "create" | null>(null);

  $effect(() => {
    if (selectedItemId) {
      const found = store.properties.find((p) => p.id === selectedItemId);
      if (found) {
        modalProperty = found;
        onclearselection?.();
      }
    }
  });

  let searchQuery = $state("");
  let statusFilter = $state("");
  let typeFilter = $state("");
  let filterModalOpen = $state(false);
  const filtersActive = $derived(statusFilter !== "" || typeFilter !== "");

  const locationMap = $derived(new Map(locationsStore.locations.map((l) => [l.id, l])));

  const filteredProperties = $derived(store.properties.filter((p) => {
    if (statusFilter && p.status !== statusFilter) return false;
    if (typeFilter && p.type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!p.name.toLowerCase().includes(q) && !p.address.toLowerCase().includes(q)) return false;
    }
    return true;
  }));

  function countByStatus(status: Property["status"]): number {
    return store.properties.filter((p) => p.status === status).length;
  }

  function statusLabel(status: Property["status"]): string {
    const map: Record<Property["status"], string> = {
      watching: "properties.status.watching",
      visited: "properties.status.visited",
      proposal_made: "properties.status.proposalMade",
      purchased: "properties.status.purchased",
      rejected: "properties.status.rejected",
    };
    return $_(map[status]);
  }

  function statusColor(status: Property["status"]): string {
    if (status === "purchased") return "#33aa66";
    if (status === "rejected") return "#cc3333";
    if (status === "proposal_made") return "#cc8833";
    if (status === "visited") return "#3388cc";
    return "#888888";
  }

  function typeLabel(type: Property["type"]): string {
    if (type === "land") return $_('properties.type.land');
    if (type === "new_build") return $_('properties.type.newBuild');
    return $_('properties.type.house');
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function sizeLabel(p: Property): string {
    const parts: string[] = [];
    if (p.builtSize != null) parts.push($_('properties.page.builtSize', { values: { size: fmt(p.builtSize) } }));
    if (p.landSize != null) parts.push($_('properties.page.landSize', { values: { size: fmt(p.landSize) } }));
    return parts.length ? parts.join(" · ") : "—";
  }
</script>

<div class="page">

  {#if store.properties.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">🏘</span>
      <p>{$_('properties.page.emptyCharts')}</p>
    </div>
  {:else}
    <div class="stat-row-wrap">
      <div class="chart-label">{$_('properties.page.searchPipeline')}</div>
      <StatTileRow>
        <StatTile label={$_('properties.status.watching')} value={countByStatus("watching")} />
        <StatTile label={$_('properties.status.visited')} value={countByStatus("visited")} />
        <StatTile label={$_('properties.status.proposalMade')} value={countByStatus("proposal_made")} />
        <StatTile label={$_('properties.status.purchased')} value={countByStatus("purchased")} />
        <StatTile label={$_('properties.status.rejected')} value={countByStatus("rejected")} />
        <StatTile label={$_('properties.page.total')} value={store.properties.length} />
      </StatTileRow>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <FilterButton active={filtersActive} title={$_('common.filters')} onclick={() => { filterModalOpen = true; }} />
      <Button iconOnly title={$_('properties.page.addProperty')} onclick={() => { modalProperty = "create"; }}>＋</Button>
    </div>

    <Modal open={filterModalOpen} title={$_('common.filters')} onclose={() => { filterModalOpen = false; }} width="360px">
      <div class="filter-modal-body">
        <select class="native-input filter-sel" bind:value={statusFilter}>
          <option value="">{$_('works.page.allStatuses')}</option>
          <option value="watching">{$_('properties.status.watching')}</option>
          <option value="visited">{$_('properties.status.visited')}</option>
          <option value="proposal_made">{$_('properties.status.proposalMade')}</option>
          <option value="purchased">{$_('properties.status.purchased')}</option>
          <option value="rejected">{$_('properties.status.rejected')}</option>
        </select>
        <select class="native-input filter-sel" bind:value={typeFilter}>
          <option value="">{$_('properties.page.allTypes')}</option>
          <option value="land">{$_('properties.type.land')}</option>
          <option value="house">{$_('properties.type.house')}</option>
          <option value="new_build">{$_('properties.type.newBuild')}</option>
        </select>
      </div>
    </Modal>

    <div class="table-wrapper">
      {#snippet emojiCell(p: Property)}
        {p.emoji}
      {/snippet}
      {#snippet nameCell(p: Property)}
        {p.name}
        {#if p.address}<span class="desc">{p.address}</span>{/if}
      {/snippet}
      {#snippet typeCell(p: Property)}
        {typeLabel(p.type)}
      {/snippet}
      {#snippet locationCell(p: Property)}
        {p.locationId ? (locationMap.get(p.locationId)?.name ?? "—") : "—"}
      {/snippet}
      {#snippet priceCell(p: Property)}
        {p.price != null ? fmt(p.price) + " €" : "—"}
      {/snippet}
      {#snippet sizeCell(p: Property)}
        {sizeLabel(p)}
      {/snippet}
      {#snippet statusCell(p: Property)}
        <span
          class="status-chip"
          style="background:{statusColor(p.status)}22;color:{statusColor(p.status)};border:1px solid {statusColor(p.status)}44"
        >{statusLabel(p.status)}</span>
      {/snippet}
      {#snippet attachmentsHeader()}
        <AttachmentIcon title={$_('common.attachments')} />
      {/snippet}
      {#snippet attachmentsCell(p: Property)}
        {#if p.attachments?.length}
          <AttachmentIcon title={$_('common.attachments')} />
        {/if}
      {/snippet}

      <SortableTable
        columns={[
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "name", label: $_('chores.editModal.name'), sortValue: (p) => p.name, cellClass: "name-cell", cell: nameCell },
          { key: "type", label: $_('properties.page.type'), sortValue: (p) => typeLabel(p.type), cell: typeCell, hideBelow: "tablet" },
          { key: "location", label: $_('properties.page.location'), sortValue: (p) => (p.locationId ? locationMap.get(p.locationId)?.name ?? null : null), cell: locationCell, hideBelow: "mobile" },
          { key: "price", label: $_('properties.page.price'), sortValue: (p) => p.price, cell: priceCell, hideBelow: "mobile" },
          { key: "size", label: $_('properties.page.size'), sortValue: (p) => p.builtSize ?? p.landSize, cell: sizeCell, hideBelow: "tablet" },
          { key: "status", label: $_('works.page.status'), sortValue: (p) => p.status, cell: statusCell },
          { key: "attachments", label: attachmentsHeader, sortValue: (p) => (p.attachments?.length ? 1 : 0), cellClass: "attachments-cell", cell: attachmentsCell, hideBelow: "mobile" },
        ] as Column<Property>[]}
        rows={filteredProperties}
        rowKey={(p) => p.id}
        rowClick={(p) => { modalProperty = p; }}
        emptyMessage={store.properties.length === 0 ? $_('properties.page.emptyNoProperties') : $_('properties.page.emptyNoMatch')}
      />
    </div>

    <div class="footer">{$_('properties.page.footer', { values: { n: filteredProperties.length } })}</div>
    </Card>
  </div>
</div>

{#if modalProperty !== null}
  <PropertyModal
    property={modalProperty === "create" ? null : modalProperty}
    {store}
    {locationsStore}
    onclose={() => { modalProperty = null; }}
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

  .stat-row-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 700px) {
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; width: 100%; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
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
  .filter-sel { cursor: pointer; }

  .filter-modal-body { display: flex; flex-direction: column; gap: var(--space-3); }
  .filter-modal-body .native-input { width: 100%; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  .desc { font-size: 11px; color: var(--text-faint); font-weight: 400; margin-left: 6px; }
  .status-chip { padding: 2px 7px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 500; }
  :global(.attachments-cell) { width: 32px; text-align: center; color: var(--text-faint); }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
