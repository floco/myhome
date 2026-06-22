<!-- packages/editor/src/lib/components/SettingsPage.svelte -->
<script lang="ts">
  import type { createSettingsStore, CostCategory, InventoryCategory, WorkCategory, Supplier } from "../settingsStore.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: SettingsStore;
  }
  let { store }: Props = $props();

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
    if (!costDraft.name.trim()) { costError = "Name required"; return; }
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
    if (!newCostDraft.name.trim()) { costError = "Name required"; return; }
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
    if (!invDraft.name.trim()) { invError = "Name required"; return; }
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
    if (!newInvDraft.name.trim()) { invError = "Name required"; return; }
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
    if (!workDraft.name.trim()) { workError = "Name required"; return; }
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
    if (!newWorkDraft.name.trim()) { workError = "Name required"; return; }
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
    if (!supplierDraft.name.trim()) { supplierError = "Name required"; return; }
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
    if (!newSupplierDraft.name.trim()) { supplierError = "Name required"; return; }
    const newS: Supplier = {
      id: crypto.randomUUID(),
      name: newSupplierDraft.name.trim(),
    };
    await store.updateSuppliers([...store.suppliers, newS]);
    newSupplierDraft = { name: "" };
    showNewSupplierForm = false;
    supplierError = null;
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>Settings</h1>
  </div>

  <div class="sections">

    <!-- Cost categories -->
    <section class="section">
      <div class="section-header">
        <h2>Cost categories</h2>
        <button class="add-btn" onclick={() => { showNewCostForm = true; costError = null; }}>＋ Add</button>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Color</th>
              <th>Emoji</th>
              <th>Name</th>
              <th>Unit</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each store.costCategories as cat (cat.id)}
              {#if editingCostId === cat.id}
                <tr class="editing-row">
                  <td><input type="color" bind:value={costDraft.color} class="color-input" /></td>
                  <td><input class="emoji-input" bind:value={costDraft.emoji} maxlength="2" /></td>
                  <td><input class="name-input" bind:value={costDraft.name} placeholder="Name" /></td>
                  <td><input class="unit-input" bind:value={costDraftUnit} placeholder="L, kWh…" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditCost} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditCost} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td><span class="color-swatch" style="background:{cat.color}"></span></td>
                  <td class="emoji-cell">{cat.emoji}</td>
                  <td>{cat.name}</td>
                  <td class="unit-cell">{cat.unit ?? "—"}</td>
                  <td class="actions">
                    {#if confirmDeleteCostId === cat.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteCostCategory(cat.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteCostId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditCost(cat)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteCostId = cat.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}

            {#if showNewCostForm}
              <tr class="editing-row">
                <td><input type="color" bind:value={newCostDraft.color} class="color-input" /></td>
                <td><input class="emoji-input" bind:value={newCostDraft.emoji} maxlength="2" placeholder="💰" /></td>
                <td><input class="name-input" bind:value={newCostDraft.name} placeholder="Name *" /></td>
                <td><input class="unit-input" bind:value={newCostDraft.unit} placeholder="L, kWh… (optional)" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addCostCategory} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewCostForm = false; costError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if costError}<div class="error">{costError}</div>{/if}
    </section>

    <!-- Inventory categories -->
    <section class="section">
      <div class="section-header">
        <h2>Inventory categories</h2>
        <button class="add-btn" onclick={() => { showNewInvForm = true; invError = null; }}>＋ Add</button>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Name</th><th></th></tr>
          </thead>
          <tbody>
            {#each store.inventoryCategories as cat (cat.id)}
              {#if editingInvId === cat.id}
                <tr class="editing-row">
                  <td><input class="name-input wide" bind:value={invDraft.name} placeholder="Name" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditInv} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditInv} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td>{cat.name}</td>
                  <td class="actions">
                    {#if confirmDeleteInvId === cat.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteInventoryCategory(cat.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteInvId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditInv(cat)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteInvId = cat.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}

            {#if showNewInvForm}
              <tr class="editing-row">
                <td><input class="name-input wide" bind:value={newInvDraft.name} placeholder="Name *" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addInventoryCategory} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewInvForm = false; invError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if invError}<div class="error">{invError}</div>{/if}
    </section>

    <!-- Work categories -->
    <section class="section">
      <div class="section-header">
        <h2>Work categories</h2>
        <button class="add-btn" onclick={() => { showNewWorkForm = true; workError = null; }}>＋ Add</button>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Emoji</th><th>Name</th><th></th></tr>
          </thead>
          <tbody>
            {#each store.workCategories as cat (cat.id)}
              {#if editingWorkId === cat.id}
                <tr class="editing-row">
                  <td><input class="emoji-input" bind:value={workDraft.emoji} maxlength="2" /></td>
                  <td><input class="name-input" bind:value={workDraft.name} placeholder="Name" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditWork} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditWork} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td class="emoji-cell">{cat.emoji}</td>
                  <td>{cat.name}</td>
                  <td class="actions">
                    {#if confirmDeleteWorkId === cat.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteWorkCategory(cat.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteWorkId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditWork(cat)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteWorkId = cat.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
            {#if showNewWorkForm}
              <tr class="editing-row">
                <td><input class="emoji-input" bind:value={newWorkDraft.emoji} maxlength="2" placeholder="🔧" /></td>
                <td><input class="name-input" bind:value={newWorkDraft.name} placeholder="Name *" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addWorkCategory} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewWorkForm = false; workError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if workError}<div class="error">{workError}</div>{/if}
    </section>

    <!-- Suppliers -->
    <section class="section">
      <div class="section-header">
        <h2>Suppliers</h2>
        <button class="add-btn" onclick={() => { showNewSupplierForm = true; supplierError = null; }}>＋ Add</button>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Name</th><th></th></tr>
          </thead>
          <tbody>
            {#each store.suppliers as s (s.id)}
              {#if editingSupplierId === s.id}
                <tr class="editing-row">
                  <td><input class="name-input wide" bind:value={supplierDraft.name} placeholder="Name" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditSupplier} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditSupplier} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td>{s.name}</td>
                  <td class="actions">
                    {#if confirmDeleteSupplierId === s.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteSupplier(s.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteSupplierId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditSupplier(s)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteSupplierId = s.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
            {#if showNewSupplierForm}
              <tr class="editing-row">
                <td><input class="name-input wide" bind:value={newSupplierDraft.name} placeholder="Name *" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addSupplier} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewSupplierForm = false; supplierError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      {#if supplierError}<div class="error">{supplierError}</div>{/if}
    </section>

  </div>
</div>

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: #141428; font-family: sans-serif; overflow-y: auto;
  }
  .page-header {
    padding: 16px 20px 8px; border-bottom: 1px solid #2a2a4a; flex-shrink: 0;
  }
  h1 { margin: 0; font-size: 16px; color: #eee; font-weight: 600; }
  .sections { padding: 16px 20px; display: flex; flex-direction: column; gap: 32px; }

  .section {}
  .section-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 10px;
  }
  h2 { margin: 0; font-size: 13px; color: #99a; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }

  .table-wrapper { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: #bbb; }
  thead { background: #1a1a30; }
  th {
    padding: 5px 10px; color: #445; font-size: 10px;
    text-transform: uppercase; letter-spacing: .05em; text-align: left;
    border-bottom: 1px solid #2a2a3a;
  }
  td { padding: 6px 10px; border-bottom: 1px solid #1e1e2e; vertical-align: middle; }
  tr:hover td { background: #1c1c38; }
  .editing-row td { background: #1a1a38; }

  .color-swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
  .emoji-cell { font-size: 15px; }
  .unit-cell { color: #667; }

  .color-input { width: 36px; height: 24px; border: 1px solid #2a2a4a; border-radius: 3px; padding: 0; cursor: pointer; background: none; }
  .emoji-input { width: 36px; background: #0f0f24; border: 1px solid #2a2a4a; color: #ccc; padding: 3px 4px; border-radius: 3px; font-size: 14px; text-align: center; }
  .name-input { width: 160px; background: #0f0f24; border: 1px solid #2a2a4a; color: #ccc; padding: 3px 7px; border-radius: 3px; font-size: 12px; }
  .name-input.wide { width: 260px; }
  .unit-input { width: 100px; background: #0f0f24; border: 1px solid #2a2a4a; color: #ccc; padding: 3px 7px; border-radius: 3px; font-size: 12px; }

  .actions { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
  .icon-action {
    background: none; border: none; color: #667; cursor: pointer; font-size: 12px;
    padding: 2px 5px; border-radius: 3px;
  }
  .icon-action:hover { background: #2a2a4a; color: #aaa; }
  .icon-action.ok { color: #4c9; }
  .icon-action.ok:hover { background: #1a3a2a; color: #6eb; }
  .icon-action.danger { color: #c66; }
  .icon-action.danger:hover { background: #2a1010; color: #f88; }
  .confirm-text { font-size: 10px; color: #c66; }

  .add-btn {
    background: #1a3a2a; border: none; color: #4c9;
    padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer;
  }
  .add-btn:hover { background: #224a34; }

  .error { color: #f44336; font-size: 11px; margin-top: 6px; }
</style>
