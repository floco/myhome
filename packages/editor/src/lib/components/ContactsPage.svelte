<!-- packages/editor/src/lib/components/ContactsPage.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createContactsStore, Contact } from "../contactsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import ContactModal from "./ContactModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import StatTile from "./ui/StatTile.svelte";
  import StatTileRow from "./ui/StatTileRow.svelte";

  type ContactsStore = ReturnType<typeof createContactsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: ContactsStore;
    settingsStore: SettingsStore;
  }
  let { store, settingsStore }: Props = $props();

  let modalContact = $state<Contact | "create" | null>(null);
  let searchQuery = $state("");
  let typeFilter = $state("");

  const typeMap = $derived(new Map(settingsStore.contactTypes.map(t => [t.id, t])));

  const typeCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const c of store.contacts) counts.set(c.typeId, (counts.get(c.typeId) ?? 0) + 1);
    return counts;
  })());

  const filteredContacts = $derived(store.contacts.filter(c => {
    if (typeFilter && c.typeId !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!c.name.toLowerCase().includes(q) && !(c.companyName ?? "").toLowerCase().includes(q)) return false;
    }
    return true;
  }));
</script>

<div class="page">
  {#if store.contacts.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">👤</span>
      <p>{$_('contacts.page.emptyCharts')}</p>
    </div>
  {:else}
    <div class="stat-row-wrap">
      <div class="chart-label">{$_('contacts.page.countByType')}</div>
      <StatTileRow>
        {#each settingsStore.contactTypes as t}
          <StatTile label={t.name} value={typeCounts.get(t.id) ?? 0} />
        {/each}
      </StatTileRow>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={typeFilter}>
        <option value="">{$_('contacts.page.allTypes')}</option>
        {#each settingsStore.contactTypes as t}
          <option value={t.id}>{t.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalContact = "create"; }}>＋ {$_('contacts.page.addContact')}</Button>
    </div>

    <div class="table-wrapper">
      {#snippet nameCell(c: Contact)}
        {c.name}
        {#if c.companyName}<span class="desc">{c.companyName}</span>{/if}
      {/snippet}
      {#snippet typeCell(c: Contact)}
        {typeMap.get(c.typeId)?.name ?? "—"}
      {/snippet}
      {#snippet phoneCell(c: Contact)}
        {c.phone ?? "—"}
      {/snippet}
      {#snippet emailCell(c: Contact)}
        {c.email ?? "—"}
      {/snippet}

      <SortableTable
        columns={[
          { key: "name", label: $_('contacts.page.name'), sortValue: (c) => c.name, cellClass: "name-cell", cell: nameCell },
          { key: "type", label: $_('contacts.page.type'), sortValue: (c) => typeMap.get(c.typeId)?.name ?? null, cell: typeCell },
          { key: "phone", label: $_('contacts.page.phone'), sortValue: (c) => c.phone, cell: phoneCell, hideBelow: "mobile" },
          { key: "email", label: $_('contacts.page.email'), sortValue: (c) => c.email, cell: emailCell, hideBelow: "tablet" },
        ] as Column<Contact>[]}
        rows={filteredContacts}
        rowKey={(c) => c.id}
        rowClick={(c) => { modalContact = c; }}
        emptyMessage={store.contacts.length === 0 ? $_('contacts.page.emptyNoContacts') : $_('contacts.page.emptyNoMatch')}
      />
    </div>

    <div class="footer">{$_('contacts.page.footer', { values: { n: filteredContacts.length } })}</div>
    </Card>
  </div>
</div>

{#if modalContact !== null}
  <ContactModal
    contact={modalContact === "create" ? null : modalContact}
    {store}
    {settingsStore}
    onclose={() => { modalContact = null; }}
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
  .chart-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  @media (max-width: 700px) {
    .page { overflow-y: auto; }
    .table-card-wrap { flex: none; min-height: auto; }
    .table-card-wrap :global(.ui-card) { flex: none !important; overflow: visible !important; min-height: auto !important; }
    .table-wrapper { flex: none !important; overflow-y: visible !important; }
  }
  .toolbar { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-sel { cursor: pointer; }
  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  .desc { font-size: 11px; color: var(--text-faint); font-weight: 400; margin-left: 6px; }
  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
