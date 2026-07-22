<!-- packages/editor/src/lib/components/settings/SettingsCategories.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createSettingsStore, CostCategory, ConsumableCategory, InventoryCategory, WorkCategory, Supplier } from "../../settingsStore.svelte";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import EmojiPicker from "../ui/EmojiPicker.svelte";
  import Card from "../ui/Card.svelte";
  import Tabs from "../ui/Tabs.svelte";
  import SortableTable from "../ui/SortableTable.svelte";
  import type { Column } from "../ui/SortableTable.types";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: SettingsStore;
  }
  let { store }: Props = $props();

  type CategoryTab = "cost" | "inventory" | "work" | "suppliers" | "consumables";
  let activeTab = $state<CategoryTab>("cost");

  // --- Cost categories ---
  let editingCostId = $state<string | null>(null);
  let costDraft = $state<CostCategory>({ id: "", name: "", emoji: "", unit: null, color: "#4466cc" });
  let costDraftUnit = $state("");
  let showNewCostForm = $state(false);
  let newCostDraft = $state({ name: "", emoji: "", unit: "", color: "#4466cc" });
  let confirmDeleteCostId = $state<string | null>(null);
  let costError = $state<string | null>(null);

  function startEditCost(cat: CostCategory): void {
    editingCostId = cat.id;
    costDraft = { ...cat };
    costDraftUnit = cat.unit ?? "";
  }

  function cancelEditCost(): void {
    editingCostId = null;
    costError = null;
  }

  async function saveEditCost(): Promise<void> {
    if (!costDraft.name.trim()) { costError = $_('settings.general.nameRequired'); return; }
    const updated = store.costCategories.map(c =>
      c.id === editingCostId ? { ...costDraft, name: costDraft.name.trim(), unit: costDraftUnit.trim() || null } : c
    );
    await store.updateCostCategories(updated);
    editingCostId = null;
    costError = null;
  }

  async function deleteCostCategory(id: string): Promise<void> {
    const updated = store.costCategories.filter(c => c.id !== id);
    await store.updateCostCategories(updated);
    confirmDeleteCostId = null;
  }

  async function addCostCategory(): Promise<void> {
    if (!newCostDraft.name.trim()) { costError = $_('settings.general.nameRequired'); return; }
    const newCat: CostCategory = {
      id: crypto.randomUUID(),
      name: newCostDraft.name.trim(),
      emoji: newCostDraft.emoji || "💰",
      unit: newCostDraft.unit.trim() || null,
      color: newCostDraft.color,
    };
    await store.updateCostCategories([...store.costCategories, newCat]);
    newCostDraft = { name: "", emoji: "", unit: "", color: "#4466cc" };
    showNewCostForm = false;
    costError = null;
  }

  // --- Inventory categories ---
  let editingInvId = $state<string | null>(null);
  let invDraft = $state<InventoryCategory>({ id: "", name: "" });
  let showNewInvForm = $state(false);
  let newInvDraft = $state({ name: "" });
  let confirmDeleteInvId = $state<string | null>(null);
  let invError = $state<string | null>(null);

  function startEditInv(cat: InventoryCategory): void {
    editingInvId = cat.id;
    invDraft = { ...cat };
    invError = null;
  }

  function cancelEditInv(): void { editingInvId = null; invError = null; }

  async function saveEditInv(): Promise<void> {
    if (!invDraft.name.trim()) { invError = $_('settings.general.nameRequired'); return; }
    const updated = store.inventoryCategories.map(c =>
      c.id === editingInvId ? { ...invDraft, name: invDraft.name.trim() } : c
    );
    await store.updateInventoryCategories(updated);
    editingInvId = null; invError = null;
  }

  async function deleteInventoryCategory(id: string): Promise<void> {
    await store.updateInventoryCategories(store.inventoryCategories.filter(c => c.id !== id));
    confirmDeleteInvId = null;
  }

  async function addInventoryCategory(): Promise<void> {
    if (!newInvDraft.name.trim()) { invError = $_('settings.general.nameRequired'); return; }
    const newCat: InventoryCategory = {
      id: crypto.randomUUID(),
      name: newInvDraft.name.trim(),
    };
    await store.updateInventoryCategories([...store.inventoryCategories, newCat]);
    newInvDraft = { name: "" };
    showNewInvForm = false;
    invError = null;
  }

  // --- Work categories ---
  let editingWorkId = $state<string | null>(null);
  let workDraft = $state<WorkCategory>({ id: "", name: "", emoji: "" });
  let showNewWorkForm = $state(false);
  let newWorkDraft = $state({ name: "", emoji: "" });
  let confirmDeleteWorkId = $state<string | null>(null);
  let workError = $state<string | null>(null);

  function startEditWork(cat: WorkCategory): void {
    editingWorkId = cat.id;
    workDraft = { ...cat };
    workError = null;
  }

  function cancelEditWork(): void { editingWorkId = null; workError = null; }

  async function saveEditWork(): Promise<void> {
    if (!workDraft.name.trim()) { workError = $_('settings.general.nameRequired'); return; }
    const updated = store.workCategories.map(c =>
      c.id === editingWorkId ? { ...workDraft, name: workDraft.name.trim() } : c
    );
    await store.updateWorkCategories(updated);
    editingWorkId = null; workError = null;
  }

  async function deleteWorkCategory(id: string): Promise<void> {
    await store.updateWorkCategories(store.workCategories.filter(c => c.id !== id));
    confirmDeleteWorkId = null;
  }

  async function addWorkCategory(): Promise<void> {
    if (!newWorkDraft.name.trim()) { workError = $_('settings.general.nameRequired'); return; }
    const newCat: WorkCategory = {
      id: crypto.randomUUID(),
      name: newWorkDraft.name.trim(),
      emoji: newWorkDraft.emoji || "🔧",
    };
    await store.updateWorkCategories([...store.workCategories, newCat]);
    newWorkDraft = { name: "", emoji: "" };
    showNewWorkForm = false; workError = null;
  }

  // --- Suppliers ---
  let editingSupplierId = $state<string | null>(null);
  let supplierDraft = $state<Supplier>({ id: "", name: "" });
  let showNewSupplierForm = $state(false);
  let newSupplierDraft = $state({ name: "" });
  let confirmDeleteSupplierId = $state<string | null>(null);
  let supplierError = $state<string | null>(null);

  function startEditSupplier(s: Supplier): void {
    editingSupplierId = s.id;
    supplierDraft = { ...s };
    supplierError = null;
  }

  function cancelEditSupplier(): void { editingSupplierId = null; supplierError = null; }

  async function saveEditSupplier(): Promise<void> {
    if (!supplierDraft.name.trim()) { supplierError = $_('settings.general.nameRequired'); return; }
    const updated = store.suppliers.map(s =>
      s.id === editingSupplierId ? { ...supplierDraft, name: supplierDraft.name.trim() } : s
    );
    await store.updateSuppliers(updated);
    editingSupplierId = null; supplierError = null;
  }

  async function deleteSupplier(id: string): Promise<void> {
    await store.updateSuppliers(store.suppliers.filter(s => s.id !== id));
    confirmDeleteSupplierId = null;
  }

  async function addSupplier(): Promise<void> {
    if (!newSupplierDraft.name.trim()) { supplierError = $_('settings.general.nameRequired'); return; }
    const newS: Supplier = {
      id: crypto.randomUUID(),
      name: newSupplierDraft.name.trim(),
    };
    await store.updateSuppliers([...store.suppliers, newS]);
    newSupplierDraft = { name: "" };
    showNewSupplierForm = false;
    supplierError = null;
  }

  // --- Consumable units ---
  let newUnit = $state("");
  let unitError = $state<string | null>(null);

  async function addUnit(): Promise<void> {
    const u = newUnit.trim();
    if (!u) return;
    if (store.consumableUnits.includes(u)) { unitError = $_('settings.categories.unitAlreadyExists'); return; }
    await store.updateConsumableUnits([...store.consumableUnits, u]);
    newUnit = "";
    unitError = null;
  }

  async function removeUnit(u: string): Promise<void> {
    await store.updateConsumableUnits(store.consumableUnits.filter((x) => x !== u));
  }

  // --- Consumable categories ---
  let editingConsumableCatId = $state<string | null>(null);
  let consumableCatDraft = $state<ConsumableCategory>({ id: "", name: "", emoji: "" });
  let showNewConsumableCatForm = $state(false);
  let newConsumableCatDraft = $state({ name: "", emoji: "" });
  let confirmDeleteConsumableCatId = $state<string | null>(null);
  let consumableCatError = $state<string | null>(null);

  function startEditConsumableCat(cat: ConsumableCategory): void {
    editingConsumableCatId = cat.id;
    consumableCatDraft = { ...cat };
    consumableCatError = null;
  }

  function cancelEditConsumableCat(): void { editingConsumableCatId = null; consumableCatError = null; }

  async function saveEditConsumableCat(): Promise<void> {
    if (!consumableCatDraft.name.trim()) { consumableCatError = $_('settings.general.nameRequired'); return; }
    const updated = store.consumableCategories.map((c) =>
      c.id === editingConsumableCatId ? { ...consumableCatDraft, name: consumableCatDraft.name.trim() } : c,
    );
    await store.updateConsumableCategories(updated);
    editingConsumableCatId = null; consumableCatError = null;
  }

  async function deleteConsumableCategory(id: string): Promise<void> {
    await store.updateConsumableCategories(store.consumableCategories.filter((c) => c.id !== id));
    confirmDeleteConsumableCatId = null;
  }

  async function addConsumableCategory(): Promise<void> {
    if (!newConsumableCatDraft.name.trim()) { consumableCatError = $_('settings.general.nameRequired'); return; }
    const newCat: ConsumableCategory = {
      id: crypto.randomUUID(),
      name: newConsumableCatDraft.name.trim(),
      emoji: newConsumableCatDraft.emoji || "📦",
    };
    await store.updateConsumableCategories([...store.consumableCategories, newCat]);
    newConsumableCatDraft = { name: "", emoji: "" };
    showNewConsumableCatForm = false;
    consumableCatError = null;
  }
</script>

<Tabs
  tabs={[
    { id: "cost", label: $_('settings.categories.tabs.cost') },
    { id: "inventory", label: $_('settings.categories.tabs.inventory') },
    { id: "work", label: $_('settings.categories.tabs.work') },
    { id: "suppliers", label: $_('settings.categories.tabs.suppliers') },
    { id: "consumables", label: $_('settings.categories.tabs.consumables') },
  ]}
  active={activeTab}
  onchange={(id) => { activeTab = id as CategoryTab; }}
/>

{#if activeTab === "cost"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.cost')}</h2>
      <Button onclick={() => { showNewCostForm = true; costError = null; }}>＋ {$_('common.add')}</Button>
    </div>

    <div class="table-wrapper">
      {#snippet costColorCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <input type="color" bind:value={costDraft.color} class="color-input" />
        {:else}
          <span class="color-swatch" style="background:{cat.color}"></span>
        {/if}
      {/snippet}
      {#snippet costEmojiCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <EmojiPicker bind:value={costDraft.emoji} />
        {:else}
          {cat.emoji}
        {/if}
      {/snippet}
      {#snippet costNameCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <Input bind:value={costDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet costUnitCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <Input bind:value={costDraftUnit} placeholder={$_('settings.categories.unitPlaceholder')} />
        {:else}
          {cat.unit ?? "—"}
        {/if}
      {/snippet}
      {#snippet costActionsCell(cat: CostCategory)}
        {#if editingCostId === cat.id}
          <button class="icon-action ok" onclick={saveEditCost} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditCost} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteCostId === cat.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteCostCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteCostId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditCost(cat)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteCostId = cat.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet costNewRow()}
        <td><input type="color" bind:value={newCostDraft.color} class="color-input" /></td>
        <td><EmojiPicker bind:value={newCostDraft.emoji} /></td>
        <td class="name-cell-input"><Input bind:value={newCostDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="unit-cell-input"><Input bind:value={newCostDraft.unit} placeholder={$_('settings.categories.unitOptionalPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addCostCategory} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewCostForm = false; costError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "color", label: $_('settings.categories.color'), sortable: false, cell: costColorCell },
          { key: "emoji", label: $_('settings.categories.emoji'), sortable: false, cellClass: "emoji-cell", cell: costEmojiCell },
          { key: "name", label: $_('settings.categories.name'), sortValue: (c) => c.name, cellClass: (c) => editingCostId === c.id ? "name-cell-input" : "", cell: costNameCell },
          { key: "unit", label: $_('settings.categories.unit'), sortValue: (c) => c.unit, cellClass: (c) => editingCostId === c.id ? "unit-cell-input" : "unit-cell", cell: costUnitCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: costActionsCell },
        ] as Column<CostCategory>[]}
        rows={store.costCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingCostId === c.id ? "editing-row" : ""}
        extraRow={showNewCostForm ? costNewRow : undefined}
      />
    </div>
    {#if costError}<div class="error">{costError}</div>{/if}
  </Card>
{/if}

{#if activeTab === "inventory"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.inventory')}</h2>
      <Button onclick={() => { showNewInvForm = true; invError = null; }}>＋ {$_('common.add')}</Button>
    </div>

    <div class="table-wrapper">
      {#snippet invNameCell(cat: InventoryCategory)}
        {#if editingInvId === cat.id}
          <Input bind:value={invDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet invActionsCell(cat: InventoryCategory)}
        {#if editingInvId === cat.id}
          <button class="icon-action ok" onclick={saveEditInv} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditInv} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteInvId === cat.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteInventoryCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteInvId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditInv(cat)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteInvId = cat.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet invNewRow()}
        <td class="name-cell-input wide"><Input bind:value={newInvDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addInventoryCategory} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewInvForm = false; invError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "name", label: $_('settings.categories.name'), sortValue: (c) => c.name, cellClass: (c) => editingInvId === c.id ? "name-cell-input wide" : "", cell: invNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: invActionsCell },
        ] as Column<InventoryCategory>[]}
        rows={store.inventoryCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingInvId === c.id ? "editing-row" : ""}
        extraRow={showNewInvForm ? invNewRow : undefined}
      />
    </div>
    {#if invError}<div class="error">{invError}</div>{/if}
  </Card>
{/if}

{#if activeTab === "work"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.work')}</h2>
      <Button onclick={() => { showNewWorkForm = true; workError = null; }}>＋ {$_('common.add')}</Button>
    </div>
    <div class="table-wrapper">
      {#snippet workEmojiCell(cat: WorkCategory)}
        {#if editingWorkId === cat.id}
          <EmojiPicker bind:value={workDraft.emoji} />
        {:else}
          {cat.emoji}
        {/if}
      {/snippet}
      {#snippet workNameCell(cat: WorkCategory)}
        {#if editingWorkId === cat.id}
          <Input bind:value={workDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet workActionsCell(cat: WorkCategory)}
        {#if editingWorkId === cat.id}
          <button class="icon-action ok" onclick={saveEditWork} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditWork} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteWorkId === cat.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteWorkCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteWorkId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditWork(cat)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteWorkId = cat.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet workNewRow()}
        <td><EmojiPicker bind:value={newWorkDraft.emoji} /></td>
        <td class="name-cell-input"><Input bind:value={newWorkDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addWorkCategory} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewWorkForm = false; workError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "emoji", label: $_('settings.categories.emoji'), sortable: false, cellClass: "emoji-cell", cell: workEmojiCell },
          { key: "name", label: $_('settings.categories.name'), sortValue: (c) => c.name, cellClass: (c) => editingWorkId === c.id ? "name-cell-input" : "", cell: workNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: workActionsCell },
        ] as Column<WorkCategory>[]}
        rows={store.workCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingWorkId === c.id ? "editing-row" : ""}
        extraRow={showNewWorkForm ? workNewRow : undefined}
      />
    </div>
    {#if workError}<div class="error">{workError}</div>{/if}
  </Card>
{/if}

{#if activeTab === "suppliers"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.suppliers')}</h2>
      <Button onclick={() => { showNewSupplierForm = true; supplierError = null; }}>＋ {$_('common.add')}</Button>
    </div>
    <div class="table-wrapper">
      {#snippet supplierNameCell(s: Supplier)}
        {#if editingSupplierId === s.id}
          <Input bind:value={supplierDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {s.name}
        {/if}
      {/snippet}
      {#snippet supplierActionsCell(s: Supplier)}
        {#if editingSupplierId === s.id}
          <button class="icon-action ok" onclick={saveEditSupplier} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditSupplier} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteSupplierId === s.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteSupplier(s.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteSupplierId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditSupplier(s)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteSupplierId = s.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet supplierNewRow()}
        <td class="name-cell-input wide"><Input bind:value={newSupplierDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addSupplier} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewSupplierForm = false; supplierError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "name", label: $_('settings.categories.name'), sortValue: (s) => s.name, cellClass: (s) => editingSupplierId === s.id ? "name-cell-input wide" : "", cell: supplierNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: supplierActionsCell },
        ] as Column<Supplier>[]}
        rows={store.suppliers}
        rowKey={(s) => s.id}
        rowClass={(s) => editingSupplierId === s.id ? "editing-row" : ""}
        extraRow={showNewSupplierForm ? supplierNewRow : undefined}
      />
    </div>
    {#if supplierError}<div class="error">{supplierError}</div>{/if}
  </Card>
{/if}

{#if activeTab === "consumables"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.consumables')}</h2>
    </div>

    <h3 class="subsection-title">{$_('settings.categories.units')}</h3>
    <div class="tag-list">
      {#each store.consumableUnits as u}
        <span class="tag">{u} <button class="tag-remove" onclick={() => removeUnit(u)}>✕</button></span>
      {/each}
    </div>
    <div class="add-row">
      <Input
        bind:value={newUnit}
        placeholder={$_('settings.categories.unitInputPlaceholder')}
        onkeydown={(e) => { if (e.key === "Enter") addUnit(); }}
      />
      <Button onclick={addUnit}>{$_('settings.categories.addUnit')}</Button>
    </div>
    {#if unitError}<div class="error">{unitError}</div>{/if}

    <h3 class="subsection-title" style="margin-top: var(--space-4)">{$_('settings.categories.categoriesHeading')}</h3>
    <div class="table-wrapper">
      {#snippet consCatEmojiCell(cat: ConsumableCategory)}
        {#if editingConsumableCatId === cat.id}
          <EmojiPicker bind:value={consumableCatDraft.emoji} />
        {:else}
          {cat.emoji}
        {/if}
      {/snippet}
      {#snippet consCatNameCell(cat: ConsumableCategory)}
        {#if editingConsumableCatId === cat.id}
          <Input bind:value={consumableCatDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet consCatActionsCell(cat: ConsumableCategory)}
        {#if editingConsumableCatId === cat.id}
          <button class="icon-action ok" onclick={saveEditConsumableCat} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditConsumableCat} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteConsumableCatId === cat.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteConsumableCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteConsumableCatId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditConsumableCat(cat)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteConsumableCatId = cat.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet consCatNewRow()}
        <td><EmojiPicker bind:value={newConsumableCatDraft.emoji} /></td>
        <td class="name-cell-input"><Input bind:value={newConsumableCatDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addConsumableCategory} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewConsumableCatForm = false; consumableCatError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "emoji", label: $_('settings.categories.emoji'), sortable: false, cellClass: "emoji-cell", cell: consCatEmojiCell },
          { key: "name", label: $_('settings.categories.name'), sortValue: (c) => c.name, cellClass: (c) => editingConsumableCatId === c.id ? "name-cell-input" : "", cell: consCatNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: consCatActionsCell },
        ] as Column<ConsumableCategory>[]}
        rows={store.consumableCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingConsumableCatId === c.id ? "editing-row" : ""}
        extraRow={showNewConsumableCatForm ? consCatNewRow : undefined}
      />
    </div>
    <div class="add-row">
      <Button onclick={() => { showNewConsumableCatForm = true; consumableCatError = null; }}>＋ {$_('settings.categories.addCategory')}</Button>
    </div>
    {#if consumableCatError}<div class="error">{consumableCatError}</div>{/if}
  </Card>
{/if}

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }

  .table-wrapper { overflow-x: auto; }
  :global(.editing-row td) { background: var(--surface-alt); }

  .color-swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
  :global(.emoji-cell) { font-size: 15px; }
  :global(.unit-cell) { color: var(--text-faint); }

  .color-input { width: 36px; height: 24px; border: 1px solid var(--border); border-radius: 3px; padding: 0; cursor: pointer; background: none; }
  :global(.name-cell-input .ui-input) { width: 160px; }
  :global(.name-cell-input.wide .ui-input) { width: 260px; }
  :global(.unit-cell-input .ui-input) { width: 100px; }

  :global(.actions) { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
  .icon-action { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; padding: 2px 5px; border-radius: 3px; }
  .icon-action:hover { background: var(--surface-hover); color: var(--text-muted); }
  .icon-action.ok { color: var(--success); }
  .icon-action.ok:hover { background: color-mix(in srgb, var(--success) 18%, var(--surface)); }
  .icon-action.danger { color: var(--danger); }
  .icon-action.danger:hover { background: color-mix(in srgb, var(--danger) 18%, var(--surface)); }
  .confirm-text { font-size: 10px; color: var(--danger); }

  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  .subsection-title { margin: 0 0 var(--space-2); font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: .05em; }
  .tag-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: var(--space-2); }
  .tag { display: flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 10px; background: var(--surface-alt); border: 1px solid var(--border); font-size: 12px; color: var(--text-muted); }
  .tag-remove { border: none; background: none; color: var(--text-faint); cursor: pointer; font-size: 9px; padding: 0 2px; line-height: 1; }
  .tag-remove:hover { color: var(--danger); }
  .add-row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; margin-top: var(--space-2); }
  .add-row :global(.ui-input) { flex: 1; min-width: 120px; }
</style>
