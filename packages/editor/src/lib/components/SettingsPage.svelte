<!-- packages/editor/src/lib/components/SettingsPage.svelte -->
<script lang="ts">
  import type { createSettingsStore, CostCategory, InventoryCategory, WorkCategory, Supplier } from "../settingsStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Card from "./ui/Card.svelte";
  import Modal from "./ui/Modal.svelte";

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

  // --- Backup & Restore ---
  let downloadingBackup = $state(false);
  let backupError = $state<string | null>(null);
  let restoreFile = $state<File | null>(null);
  let showRestoreConfirm = $state(false);
  let restoringBackup = $state(false);
  let restoreSuccess = $state(false);
  let restoreError = $state<string | null>(null);
  let fileInputEl: HTMLInputElement | undefined = $state();

  async function downloadBackup(): Promise<void> {
    downloadingBackup = true;
    backupError = null;
    restoreSuccess = false;
    try {
      const resp = await fetch("/api/backup/download");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const disposition = resp.headers.get("content-disposition") ?? "";
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match ? match[1] : "myhome-backup.zip";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      backupError = "Backup failed. Please try again.";
    } finally {
      downloadingBackup = false;
    }
  }

  function onFileSelected(e: Event): void {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    restoreFile = file;
    restoreError = null;
    restoreSuccess = false;
    showRestoreConfirm = true;
  }

  async function confirmRestore(): Promise<void> {
    if (!restoreFile) return;
    restoringBackup = true;
    restoreError = null;
    try {
      const form = new FormData();
      form.append("file", restoreFile);
      const resp = await fetch("/api/backup/restore", { method: "POST", body: form });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        const msg = (data as { detail?: string }).detail ?? `HTTP ${resp.status}`;
        throw new Error(msg);
      }
      restoreSuccess = true;
      showRestoreConfirm = false;
    } catch (e) {
      restoreError = e instanceof Error ? e.message : "Restore failed.";
    } finally {
      restoringBackup = false;
      restoreFile = null;
      if (fileInputEl) fileInputEl.value = "";
    }
  }

  function cancelRestore(): void {
    showRestoreConfirm = false;
    restoreFile = null;
    restoreError = null;
    if (fileInputEl) fileInputEl.value = "";
  }
</script>

<div class="page">
  <div class="page-header">
    <h1>Settings</h1>
  </div>

  <div class="sections">

    <!-- Cost categories -->
    <Card>
      <div class="section-header">
        <h2>Cost categories</h2>
        <Button onclick={() => { showNewCostForm = true; costError = null; }}>＋ Add</Button>
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
                  <td class="name-cell-input"><Input bind:value={costDraft.name} placeholder="Name" /></td>
                  <td class="unit-cell-input"><Input bind:value={costDraftUnit} placeholder="L, kWh…" /></td>
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
                <td class="name-cell-input"><Input bind:value={newCostDraft.name} placeholder="Name *" /></td>
                <td class="unit-cell-input"><Input bind:value={newCostDraft.unit} placeholder="L, kWh… (optional)" /></td>
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
    </Card>

    <!-- Inventory categories -->
    <Card>
      <div class="section-header">
        <h2>Inventory categories</h2>
        <Button onclick={() => { showNewInvForm = true; invError = null; }}>＋ Add</Button>
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
                  <td class="name-cell-input wide"><Input bind:value={invDraft.name} placeholder="Name" /></td>
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
                <td class="name-cell-input wide"><Input bind:value={newInvDraft.name} placeholder="Name *" /></td>
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
    </Card>

    <!-- Work categories -->
    <Card>
      <div class="section-header">
        <h2>Work categories</h2>
        <Button onclick={() => { showNewWorkForm = true; workError = null; }}>＋ Add</Button>
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
                  <td class="name-cell-input"><Input bind:value={workDraft.name} placeholder="Name" /></td>
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
                <td class="name-cell-input"><Input bind:value={newWorkDraft.name} placeholder="Name *" /></td>
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
    </Card>

    <!-- Suppliers -->
    <Card>
      <div class="section-header">
        <h2>Suppliers</h2>
        <Button onclick={() => { showNewSupplierForm = true; supplierError = null; }}>＋ Add</Button>
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
                  <td class="name-cell-input wide"><Input bind:value={supplierDraft.name} placeholder="Name" /></td>
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
                <td class="name-cell-input wide"><Input bind:value={newSupplierDraft.name} placeholder="Name *" /></td>
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
    </Card>

    <!-- Backup & Restore -->
    <Card>
      <div class="section-header">
        <h2>Backup & Restore</h2>
      </div>
      <div class="backup-actions">
        <div class="backup-action">
          <p class="backup-desc">Download a zip archive of all your data.</p>
          <Button onclick={downloadBackup} disabled={downloadingBackup}>
            {downloadingBackup ? "Downloading…" : "Download Backup"}
          </Button>
        </div>
        <div class="backup-action">
          <p class="backup-desc">Replace all current data from a previously downloaded backup.</p>
          <Button variant="secondary" onclick={() => fileInputEl?.click()}>Restore from Backup</Button>
          <input
            bind:this={fileInputEl}
            type="file"
            accept=".zip"
            class="hidden-file-input"
            onchange={onFileSelected}
          />
        </div>
      </div>
      {#if backupError}<div class="error">{backupError}</div>{/if}
      {#if restoreError}<div class="error">{restoreError}</div>{/if}
      {#if restoreSuccess}<div class="success-msg">Restore complete. Reload the page to see updated data.</div>{/if}
    </Card>

  </div>
</div>

<Modal open={showRestoreConfirm} title="Restore Backup" onclose={cancelRestore} width="400px">
  {#snippet children()}
    <p class="restore-warning">This will replace all current data with the contents of the backup. This cannot be undone.</p>
  {/snippet}
  {#snippet footer()}
    <Button variant="secondary" onclick={cancelRestore}>Cancel</Button>
    <Button onclick={confirmRestore} disabled={restoringBackup}>
      {restoringBackup ? "Restoring…" : "Restore"}
    </Button>
  {/snippet}
</Modal>

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: var(--bg); font-family: var(--font-sans); overflow-y: auto;
  }
  .page-header {
    padding: var(--space-4) var(--space-4) var(--space-2); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  h1 { margin: 0; font-size: 16px; color: var(--text); font-weight: 600; }
  .sections { padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-5); }

  .section-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: var(--space-2);
  }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }

  .table-wrapper { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { background: var(--surface-alt); }
  th {
    padding: 5px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: .05em; text-align: left;
    border-bottom: 1px solid var(--border);
  }
  td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); }
  .editing-row td { background: var(--surface-alt); }

  .color-swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
  .emoji-cell { font-size: 15px; }
  .unit-cell { color: var(--text-faint); }

  .color-input { width: 36px; height: 24px; border: 1px solid var(--border); border-radius: 3px; padding: 0; cursor: pointer; background: none; }
  .emoji-input {
    width: 36px; background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 3px 4px; border-radius: 3px; font-size: 14px; text-align: center;
  }
  .name-cell-input :global(.ui-input) { width: 160px; }
  .name-cell-input.wide :global(.ui-input) { width: 260px; }
  .unit-cell-input :global(.ui-input) { width: 100px; }

  .actions { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
  .icon-action {
    background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px;
    padding: 2px 5px; border-radius: 3px;
  }
  .icon-action:hover { background: var(--surface-hover); color: var(--text-muted); }
  .icon-action.ok { color: var(--success); }
  .icon-action.ok:hover { background: color-mix(in srgb, var(--success) 18%, var(--surface)); }
  .icon-action.danger { color: var(--danger); }
  .icon-action.danger:hover { background: color-mix(in srgb, var(--danger) 18%, var(--surface)); }
  .confirm-text { font-size: 10px; color: var(--danger); }

  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }
</style>
