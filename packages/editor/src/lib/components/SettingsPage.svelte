<!-- packages/editor/src/lib/components/SettingsPage.svelte -->
<script lang="ts">
  import type { createSettingsStore, CostCategory, ConsumableCategory, InventoryCategory, WorkCategory, Supplier } from "../settingsStore.svelte";
  import type { createAuthStore } from "../authStore.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import Card from "./ui/Card.svelte";
  import Modal from "./ui/Modal.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type AuthStore = ReturnType<typeof createAuthStore>;

  interface Props {
    store: SettingsStore;
    authStore: AuthStore;
  }
  let { store, authStore }: Props = $props();

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

  // --- Consumable units ---
  let newUnit = $state("");
  let unitError = $state<string | null>(null);

  async function addUnit(): Promise<void> {
    const u = newUnit.trim();
    if (!u) return;
    if (store.consumableUnits.includes(u)) { unitError = "Unit already exists"; return; }
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
    if (!consumableCatDraft.name.trim()) { consumableCatError = "Name required"; return; }
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
    if (!newConsumableCatDraft.name.trim()) { consumableCatError = "Name required"; return; }
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

  // --- Notifications ---
  let notifDraft = $state({ ...store.notificationSettings, haNotifyService: store.notificationSettings.haNotifyService ?? "" });
  let notifChoresThresholdStr = $state(String(store.notificationSettings.choresDueSoonThreshold));
  let notifWarrantyDaysStr = $state(String(store.notificationSettings.warrantyDaysThreshold));
  let notifSynced = $state(false);
  let notifError = $state<string | null>(null);
  let notifSaving = $state(false);

  $effect(() => {
    if (store.loaded && !notifSynced) {
      notifDraft = { ...store.notificationSettings, haNotifyService: store.notificationSettings.haNotifyService ?? "" };
      notifChoresThresholdStr = String(store.notificationSettings.choresDueSoonThreshold);
      notifWarrantyDaysStr = String(store.notificationSettings.warrantyDaysThreshold);
      notifSynced = true;
    }
  });

  async function saveNotificationSettings(): Promise<void> {
    notifError = null;
    notifSaving = true;
    try {
      await store.updateNotificationSettings({
        ...notifDraft,
        haNotifyService: notifDraft.haNotifyService.trim() || null,
        choresDueSoonThreshold: parseFloat(notifChoresThresholdStr) || 0,
        warrantyDaysThreshold: parseInt(notifWarrantyDaysStr, 10) || 0,
      });
    } catch (e) {
      notifError = e instanceof Error ? e.message : String(e);
    } finally {
      notifSaving = false;
    }
  }

  // --- API Tokens ---
  interface TokenInfo {
    id: string;
    name: string;
    role: string;
    owner_id: string;
    created_at: string;
    last_used_at: string | null;
  }

  let apiTokens = $state<TokenInfo[]>([]);
  let tokensLoaded = $state(false);
  let showNewTokenModal = $state(false);
  let newTokenName = $state("");
  let newTokenRole = $state<string>("ro");
  let createdTokenSecret = $state<string | null>(null);
  let confirmRevokeTokenId = $state<string | null>(null);
  let tokenError = $state<string | null>(null);

  const _allRoles = ["ro", "normal", "admin"];
  const roleOptions = $derived(
    _allRoles.slice(0, _allRoles.indexOf(authStore.user?.role ?? "ro") + 1)
  );

  async function loadTokens(): Promise<void> {
    try {
      const resp = await fetch("/api/auth/tokens");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      apiTokens = await resp.json();
    } finally {
      tokensLoaded = true;
    }
  }

  async function createApiToken(): Promise<void> {
    if (!newTokenName.trim()) { tokenError = "Name required"; return; }
    tokenError = null;
    const resp = await fetch("/api/auth/tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newTokenName.trim(), role: newTokenRole }),
    });
    if (!resp.ok) { tokenError = `Error ${resp.status}`; return; }
    const data = await resp.json();
    createdTokenSecret = data.token;
    newTokenName = "";
    newTokenRole = "ro";
    showNewTokenModal = false;
    await loadTokens();
  }

  async function revokeToken(id: string): Promise<void> {
    await fetch(`/api/auth/tokens/${id}`, { method: "DELETE" });
    confirmRevokeTokenId = null;
    await loadTokens();
  }

  loadTokens();

  // --- User management (admin only) ---
  interface UserInfo {
    id: string;
    username: string;
    role: string;
    created_at: string;
  }

  let users = $state<UserInfo[]>([]);
  let usersLoaded = $state(false);
  let showNewUserModal = $state(false);
  let newUserName = $state("");
  let newUserPassword = $state("");
  let newUserRole = $state<string>("normal");
  let userError = $state<string | null>(null);
  let editingUserId = $state<string | null>(null);
  let editUserRole = $state<string>("normal");
  let resetPasswordUserId = $state<string | null>(null);
  let resetPasswordValue = $state("");
  let confirmDeleteUserId = $state<string | null>(null);

  async function loadUsers(): Promise<void> {
    if (authStore.user?.role !== "admin") return;
    try {
      const resp = await fetch("/api/auth/users");
      if (!resp.ok) return;
      users = await resp.json();
    } finally {
      usersLoaded = true;
    }
  }

  async function createUser(): Promise<void> {
    if (!newUserName.trim()) { userError = "Username required"; return; }
    if (newUserPassword.length < 8) { userError = "Password must be at least 8 characters"; return; }
    userError = null;
    const resp = await fetch("/api/auth/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: newUserName.trim(), password: newUserPassword, role: newUserRole }),
    });
    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      userError = (d as { detail?: string }).detail ?? `Error ${resp.status}`;
      return;
    }
    showNewUserModal = false;
    newUserName = "";
    newUserPassword = "";
    newUserRole = "normal";
    await loadUsers();
  }

  async function updateUserRole(uid: string, role: string): Promise<void> {
    await fetch(`/api/auth/users/${uid}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    editingUserId = null;
    await loadUsers();
  }

  async function resetUserPassword(uid: string): Promise<void> {
    if (resetPasswordValue.length < 8) return;
    await fetch(`/api/auth/users/${uid}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: resetPasswordValue }),
    });
    resetPasswordUserId = null;
    resetPasswordValue = "";
  }

  async function deleteUser(uid: string): Promise<void> {
    await fetch(`/api/auth/users/${uid}`, { method: "DELETE" });
    confirmDeleteUserId = null;
    await loadUsers();
  }

  loadUsers();

  // --- MCP Server (admin only) ---
  let mcpEnabled = $state(false);
  let mcpConfigLoaded = $state(false);
  let mcpError = $state<string | null>(null);

  async function loadMcpConfig(): Promise<void> {
    if (authStore.user?.role !== "admin") return;
    try {
      const resp = await fetch("/api/mcp/config");
      if (!resp.ok) return;
      const data = await resp.json();
      mcpEnabled = data.enabled;
    } finally {
      mcpConfigLoaded = true;
    }
  }

  async function toggleMcpEnabled(): Promise<void> {
    const next = !mcpEnabled;
    mcpError = null;
    const resp = await fetch("/api/mcp/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: next }),
    });
    if (!resp.ok) { mcpError = `Error ${resp.status}`; return; }
    mcpEnabled = next;
  }

  loadMcpConfig();

  // --- Single Sign-On / OIDC (admin only) ---
  interface OidcConfigInfo {
    enabled: boolean;
    provider_name: string;
    issuer: string;
    client_id: string;
    client_secret: string;
    default_role: string;
    scopes: string[];
  }

  let oidcConfig = $state<OidcConfigInfo>({
    enabled: false, provider_name: "", issuer: "", client_id: "",
    client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"],
  });
  let oidcConfigLoaded = $state(false);
  let oidcClientSecretDraft = $state("");
  let oidcError = $state<string | null>(null);
  let oidcSaving = $state(false);

  async function loadOidcConfig(): Promise<void> {
    if (authStore.user?.role !== "admin") return;
    try {
      const resp = await fetch("/api/auth/oidc/config");
      if (!resp.ok) return;
      oidcConfig = await resp.json();
    } finally {
      oidcConfigLoaded = true;
    }
  }

  async function saveOidcConfig(): Promise<void> {
    oidcError = null;
    oidcSaving = true;
    try {
      const body: Record<string, unknown> = {
        enabled: oidcConfig.enabled,
        provider_name: oidcConfig.provider_name,
        issuer: oidcConfig.issuer,
        client_id: oidcConfig.client_id,
        default_role: oidcConfig.default_role,
        scopes: oidcConfig.scopes,
      };
      if (oidcClientSecretDraft.trim()) body.client_secret = oidcClientSecretDraft.trim();
      const resp = await fetch("/api/auth/oidc/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}));
        oidcError = (d as { detail?: string }).detail ?? `Error ${resp.status}`;
        return;
      }
      oidcConfig = await resp.json();
      oidcClientSecretDraft = "";
    } finally {
      oidcSaving = false;
    }
  }

  loadOidcConfig();

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

  import { homesStore } from "../homesStore.svelte";

  // --- Home metadata ---
  let editingHomeName = $state(false);
  let homeNameDraft = $state("");
  let showDeleteConfirm = $state(false);
  let deleteError = $state<string | null>(null);
  let homeNameError = $state<string | null>(null);

  function startEditHomeName(): void {
    homeNameDraft = homesStore.activeHome?.name ?? "";
    editingHomeName = true;
    homeNameError = null;
  }

  async function saveHomeName(): Promise<void> {
    if (!homeNameDraft.trim()) { homeNameError = "Name required"; return; }
    const id = homesStore.activeHomeId;
    if (!id) return;
    try {
      await homesStore.patchHome(id, { name: homeNameDraft.trim() });
      editingHomeName = false;
    } catch (e) {
      homeNameError = e instanceof Error ? e.message : "Failed to save";
    }
  }

  let homeTypeError = $state<string | null>(null);

  async function toggleHomeType(): Promise<void> {
    const home = homesStore.activeHome;
    if (!home) return;
    const next = home.type === "existing" ? "project" : "existing";
    try {
      homeTypeError = null;
      await homesStore.patchHome(home.id, { type: next });
    } catch (e) {
      homeTypeError = e instanceof Error ? e.message : "Failed to update type";
    }
  }

  let moduleToggleWarning = $state<string | null>(null);

  async function toggleModule(moduleId: string): Promise<void> {
    const home = homesStore.activeHome;
    if (!home) return;
    const current = home.enabledModules;
    const isDisabling = current.includes(moduleId);
    if (isDisabling) {
      moduleToggleWarning = `This hides ${CORE_MODULES.concat(PROJECT_MODULES).find(m => m.id === moduleId)?.label ?? moduleId} but does not delete your data.`;
    }
    const next = isDisabling
      ? current.filter((m) => m !== moduleId)
      : [...current, moduleId];
    await homesStore.patchHome(home.id, { enabledModules: next });
  }

  async function confirmDeleteHome(): Promise<void> {
    const id = homesStore.activeHomeId;
    if (!id) return;
    try {
      await homesStore.deleteHome(id);
      showDeleteConfirm = false;
    } catch (e) {
      deleteError = e instanceof Error ? e.message : "Failed to delete home";
    }
  }

  const CORE_MODULES = [
    { id: "home",        icon: "🏡", label: "Home"           },
    { id: "plan",        icon: "📐", label: "Floor Plan"     },
    { id: "chores",      icon: "✅", label: "Chores"         },
    { id: "inventory",   icon: "📦", label: "Inventory"      },
    { id: "consumables", icon: "🛒", label: "Consumables"    },
    { id: "works",       icon: "🔧", label: "Works"          },
    { id: "kb",          icon: "📖", label: "Knowledge Base" },
    { id: "costs",       icon: "💶", label: "Costs"          },
  ];

  const PROJECT_MODULES = [
    { id: "locations",  icon: "🌍", label: "Locations"  },
    { id: "properties", icon: "🏘", label: "Properties" },
    { id: "budget",     icon: "💰", label: "Budget"     },
    { id: "visits",     icon: "📅", label: "Visits"     },
    { id: "contacts",   icon: "👤", label: "Contacts"   },
    { id: "checklist",  icon: "✅", label: "Checklist"  },
  ];
</script>

<div class="page">
  <div class="page-header">
    <h1>Settings</h1>
  </div>

  <div class="sections">

    <!-- Home metadata -->
    <Card>
      <h2 class="section-title">Home</h2>

      <div class="home-row">
        <span class="home-label">Name</span>
        {#if editingHomeName}
          <div class="home-edit-row">
            <Input bind:value={homeNameDraft} placeholder="Home name" />
            <Button onclick={saveHomeName}>Save</Button>
            <Button variant="ghost" onclick={() => { editingHomeName = false; }}>Cancel</Button>
          </div>
          {#if homeNameError}<p class="field-error">{homeNameError}</p>{/if}
        {:else}
          <span class="home-value">{homesStore.activeHome?.name ?? "—"}</span>
          <Button variant="ghost" onclick={startEditHomeName}>Edit</Button>
        {/if}
      </div>

      <div class="home-row">
        <span class="home-label">Type</span>
        <span class="home-value">
          {homesStore.activeHome?.type === "project" ? "🏗 Project home" : "🏠 Existing home"}
        </span>
        <Button variant="ghost" onclick={toggleHomeType}>Change</Button>
      </div>
      {#if homeTypeError}<p class="field-error">{homeTypeError}</p>{/if}

      <div class="home-row danger-row">
        <Button
          variant="danger"
          disabled={homesStore.homes.length <= 1}
          onclick={() => { showDeleteConfirm = true; }}
          title={homesStore.homes.length <= 1 ? "Cannot delete the only home" : undefined}
        >
          Delete this home
        </Button>
      </div>
    </Card>

    <!-- Module toggles -->
    <Card>
      <h2 class="section-title">Modules</h2>
      <p class="section-desc">Choose which modules are visible in the nav for this home.</p>

      {#if moduleToggleWarning}
        <p class="module-warning">{moduleToggleWarning}</p>
      {/if}

      <div class="module-group">
        <h3 class="group-label">Core modules</h3>
        {#each CORE_MODULES as mod (mod.id)}
          <label class="module-row">
            <input
              type="checkbox"
              checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
              onchange={() => toggleModule(mod.id)}
            />
            <span class="mod-icon">{mod.icon}</span>
            <span class="mod-label">{mod.label}</span>
          </label>
        {/each}
      </div>

      <div class="module-group">
        <h3 class="group-label">Project modules <span class="soon-tag">Placeholder</span></h3>
        {#each PROJECT_MODULES as mod (mod.id)}
          <label class="module-row">
            <input
              type="checkbox"
              checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
              onchange={() => toggleModule(mod.id)}
            />
            <span class="mod-icon">{mod.icon}</span>
            <span class="mod-label">{mod.label}</span>
          </label>
        {/each}
      </div>
    </Card>

    <!-- Delete confirmation modal -->
    <Modal open={showDeleteConfirm} title="Delete home" onclose={() => { showDeleteConfirm = false; }}>
      <p>Delete <strong>{homesStore.activeHome?.name}</strong>? This permanently removes all data for this home and cannot be undone.</p>
      {#if deleteError}<p class="field-error">{deleteError}</p>{/if}
      {#snippet footer()}
        <Button variant="ghost" onclick={() => { showDeleteConfirm = false; }}>Cancel</Button>
        <Button variant="danger" onclick={confirmDeleteHome}>Delete</Button>
      {/snippet}
    </Modal>

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
                  <td><EmojiPicker bind:value={costDraft.emoji} /></td>
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
                <td><EmojiPicker bind:value={newCostDraft.emoji} /></td>
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
                  <td><EmojiPicker bind:value={workDraft.emoji} /></td>
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
                <td><EmojiPicker bind:value={newWorkDraft.emoji} /></td>
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

    <!-- Consumables -->
    <Card>
      <div class="section-header">
        <h2>Consumables</h2>
      </div>

      <h3 class="subsection-title">Units</h3>
      <div class="tag-list">
        {#each store.consumableUnits as u}
          <span class="tag">{u} <button class="tag-remove" onclick={() => removeUnit(u)}>✕</button></span>
        {/each}
      </div>
      <div class="add-row">
        <Input
          bind:value={newUnit}
          placeholder="e.g. tablets"
          onkeydown={(e) => { if (e.key === "Enter") addUnit(); }}
        />
        <Button onclick={addUnit}>Add unit</Button>
      </div>
      {#if unitError}<div class="error">{unitError}</div>{/if}

      <h3 class="subsection-title" style="margin-top: var(--space-4)">Categories</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Emoji</th><th>Name</th><th></th></tr>
          </thead>
          <tbody>
            {#each store.consumableCategories as cat (cat.id)}
              {#if editingConsumableCatId === cat.id}
                <tr class="editing-row">
                  <td><EmojiPicker bind:value={consumableCatDraft.emoji} /></td>
                  <td class="name-cell-input"><Input bind:value={consumableCatDraft.name} placeholder="Name" /></td>
                  <td class="actions">
                    <button class="icon-action ok" onclick={saveEditConsumableCat} title="Save">✓</button>
                    <button class="icon-action" onclick={cancelEditConsumableCat} title="Cancel">✕</button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td class="emoji-cell">{cat.emoji}</td>
                  <td>{cat.name}</td>
                  <td class="actions">
                    {#if confirmDeleteConsumableCatId === cat.id}
                      <span class="confirm-text">Delete?</span>
                      <button class="icon-action danger" onclick={() => deleteConsumableCategory(cat.id)}>✓</button>
                      <button class="icon-action" onclick={() => { confirmDeleteConsumableCatId = null; }}>✕</button>
                    {:else}
                      <button class="icon-action" onclick={() => startEditConsumableCat(cat)} title="Edit">✏</button>
                      <button class="icon-action danger" onclick={() => { confirmDeleteConsumableCatId = cat.id; }} title="Delete">🗑</button>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
            {#if showNewConsumableCatForm}
              <tr class="editing-row">
                <td><EmojiPicker bind:value={newConsumableCatDraft.emoji} /></td>
                <td class="name-cell-input"><Input bind:value={newConsumableCatDraft.name} placeholder="Name *" /></td>
                <td class="actions">
                  <button class="icon-action ok" onclick={addConsumableCategory} title="Add">✓</button>
                  <button class="icon-action" onclick={() => { showNewConsumableCatForm = false; consumableCatError = null; }} title="Cancel">✕</button>
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
      <div class="add-row">
        <Button onclick={() => { showNewConsumableCatForm = true; consumableCatError = null; }}>＋ Add category</Button>
      </div>
      {#if consumableCatError}<div class="error">{consumableCatError}</div>{/if}
    </Card>

    <!-- Notifications -->
    <Card>
      <div class="section-header">
        <h2>Notifications</h2>
      </div>
      <p class="section-desc">
        Surface chores due soon, low-stock consumables, and expiring warranties in
        one place, with an optional daily summary pushed to Home Assistant.
      </p>
      <label class="module-row">
        <input class="notif-enable-toggle" type="checkbox" bind:checked={notifDraft.enabled} />
        <span class="mod-label">Enable notification center</span>
      </label>
      {#if notifDraft.enabled}
        <div class="modal-form" style="margin-top: var(--space-3)">
          <div class="modal-field">
            <span class="modal-label">Chores "due soon" threshold (fraction of period remaining)</span>
            <Input type="number" bind:value={notifChoresThresholdStr} />
          </div>
          <div class="modal-field">
            <span class="modal-label">Warranty "expiring soon" window (days)</span>
            <Input type="number" bind:value={notifWarrantyDaysStr} />
          </div>
          <label class="module-row">
            <input type="checkbox" bind:checked={notifDraft.haPushEnabled} />
            <span class="mod-label">Send a daily digest via Home Assistant</span>
          </label>
          {#if notifDraft.haPushEnabled}
            <div class="modal-field">
              <span class="modal-label">HA notify service</span>
              <Input bind:value={notifDraft.haNotifyService} placeholder="e.g. notify.mobile_app_pixel" />
            </div>
            <div class="modal-field">
              <span class="modal-label">Digest time (UTC, HH:MM)</span>
              <Input bind:value={notifDraft.haPushTime} placeholder="08:00" />
            </div>
          {/if}
        </div>
      {/if}
      {#if notifError}<div class="error">{notifError}</div>{/if}
      <div class="modal-actions">
        <Button onclick={saveNotificationSettings} disabled={notifSaving}>{notifSaving ? "Saving…" : "Save"}</Button>
      </div>
    </Card>

    <!-- API Tokens -->
    <Card>
      <div class="section-header">
        <h2>API Tokens</h2>
        <Button onclick={() => { showNewTokenModal = true; tokenError = null; }}>New token</Button>
      </div>
      <p class="section-desc">Tokens for automation, MCP, and API access. A token's scope cannot exceed your own role.</p>
      {#if tokensLoaded}
        {#if apiTokens.length === 0}
          <p class="empty-hint">No tokens yet.</p>
        {:else}
          <table class="token-table">
            <thead>
              <tr><th>Name</th><th>Scope</th><th>Created</th><th>Last used</th><th></th></tr>
            </thead>
            <tbody>
              {#each apiTokens as t (t.id)}
                <tr>
                  <td>{t.name}</td>
                  <td><span class="role-badge">{t.role}</span></td>
                  <td>{t.created_at?.slice(0, 10) ?? "—"}</td>
                  <td>{t.last_used_at ? t.last_used_at.slice(0, 10) : "—"}</td>
                  <td>
                    {#if confirmRevokeTokenId === t.id}
                      <Button variant="danger" onclick={() => revokeToken(t.id)}>Confirm revoke</Button>
                      <Button variant="secondary" onclick={() => { confirmRevokeTokenId = null; }}>Cancel</Button>
                    {:else}
                      <Button variant="secondary" onclick={() => { confirmRevokeTokenId = t.id; }}>Revoke</Button>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      {/if}
    </Card>

    <!-- Users (admin only) -->
    {#if authStore.user?.role === "admin"}
      <Card>
        <div class="section-header">
          <h2>Users</h2>
          <Button onclick={() => { showNewUserModal = true; userError = null; }}>New user</Button>
        </div>
        {#if usersLoaded}
          <table class="token-table">
            <thead>
              <tr><th>Username</th><th>Role</th><th>Created</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {#each users as u (u.id)}
                <tr>
                  <td>{u.username}</td>
                  <td>
                    {#if editingUserId === u.id}
                      <select bind:value={editUserRole} class="modal-select">
                        {#each ["ro", "normal", "admin"] as r}
                          <option value={r}>{r}</option>
                        {/each}
                      </select>
                      <Button onclick={() => updateUserRole(u.id, editUserRole)}>Save</Button>
                      <Button variant="secondary" onclick={() => { editingUserId = null; }}>Cancel</Button>
                    {:else}
                      <span class="role-badge">{u.role}</span>
                    {/if}
                  </td>
                  <td>{u.created_at?.slice(0, 10) ?? "—"}</td>
                  <td style="display:flex;gap:4px;flex-wrap:wrap">
                    {#if editingUserId !== u.id}
                      <Button variant="secondary" onclick={() => { editingUserId = u.id; editUserRole = u.role; }}>Edit role</Button>
                    {/if}
                    {#if resetPasswordUserId === u.id}
                      <input
                        type="password"
                        bind:value={resetPasswordValue}
                        placeholder="New password (min 8)"
                        class="inline-pw-input"
                      />
                      <Button onclick={() => resetUserPassword(u.id)}>Set</Button>
                      <Button variant="secondary" onclick={() => { resetPasswordUserId = null; resetPasswordValue = ""; }}>Cancel</Button>
                    {:else}
                      <Button variant="secondary" onclick={() => { resetPasswordUserId = u.id; }}>Reset pw</Button>
                    {/if}
                    {#if u.id !== authStore.user?.id}
                      {#if confirmDeleteUserId === u.id}
                        <Button variant="danger" onclick={() => deleteUser(u.id)}>Confirm delete</Button>
                        <Button variant="secondary" onclick={() => { confirmDeleteUserId = null; }}>Cancel</Button>
                      {:else}
                        <Button variant="secondary" onclick={() => { confirmDeleteUserId = u.id; }}>Delete</Button>
                      {/if}
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </Card>
    {/if}

    <!-- MCP Server (admin only) -->
    {#if authStore.user?.role === "admin"}
      <Card>
        <div class="section-header">
          <h2>MCP Server</h2>
        </div>
        <p class="section-desc">
          Lets an MCP client (Claude Desktop, claude.ai, Claude Code, or Home Assistant's
          Assist) query and act on this home's data. Create an API token above with the
          access level you want the assistant to have, then use it as the Bearer token
          when connecting.
        </p>
        {#if mcpConfigLoaded}
          <label class="module-row">
            <input type="checkbox" checked={mcpEnabled} onchange={toggleMcpEnabled} />
            <span class="mod-label">Enable MCP Server</span>
          </label>
          {#if mcpEnabled}
            <p class="empty-hint">Connection URL: <code>{window.location.origin}/mcp</code></p>
          {/if}
        {/if}
        {#if mcpError}<div class="error">{mcpError}</div>{/if}
      </Card>
    {/if}

    <!-- Single Sign-On (admin only) -->
    {#if authStore.user?.role === "admin"}
      <Card>
        <div class="section-header">
          <h2>Single Sign-On</h2>
        </div>
        <p class="section-desc">
          Let users sign in via an external OIDC provider (Keycloak, Authentik, Google
          Workspace, etc.) alongside local username/password login.
        </p>
        {#if oidcConfigLoaded}
          <label class="module-row">
            <input type="checkbox" bind:checked={oidcConfig.enabled} />
            <span class="mod-label">Enable Single Sign-On</span>
          </label>
          <div class="modal-form" style="margin-top: var(--space-3)">
            <div class="modal-field">
              <span class="modal-label">Provider name</span>
              <Input bind:value={oidcConfig.provider_name} placeholder="e.g. Keycloak" />
            </div>
            <div class="modal-field">
              <span class="modal-label">Issuer URL</span>
              <Input bind:value={oidcConfig.issuer} placeholder="https://auth.example.com/realms/home" />
            </div>
            <div class="modal-field">
              <span class="modal-label">Client ID</span>
              <Input bind:value={oidcConfig.client_id} />
            </div>
            <div class="modal-field">
              <span class="modal-label">Client secret</span>
              <Input type="password" bind:value={oidcClientSecretDraft} placeholder={oidcConfig.client_secret || "Not set"} />
            </div>
            <div class="modal-field">
              <span class="modal-label">Default role for new sign-ins</span>
              <select bind:value={oidcConfig.default_role} class="modal-select">
                {#each ["ro", "normal", "admin"] as r}
                  <option value={r}>{r}</option>
                {/each}
              </select>
            </div>
            <div class="modal-field">
              <span class="modal-label">Redirect URI</span>
              <p class="empty-hint">{window.location.origin}/api/auth/oidc/callback</p>
            </div>
            {#if oidcError}<div class="error">{oidcError}</div>{/if}
            <div class="modal-actions">
              <Button onclick={saveOidcConfig} disabled={oidcSaving}>{oidcSaving ? "Saving…" : "Save"}</Button>
            </div>
          </div>
        {/if}
      </Card>
    {/if}

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

<Modal open={showNewTokenModal} title="New API Token" onclose={() => { showNewTokenModal = false; tokenError = null; }}>
  {#snippet children()}
    <div class="modal-form">
      <div class="modal-field">
        <span class="modal-label">Token name</span>
        <Input bind:value={newTokenName} placeholder="e.g. Home Assistant MCP" />
      </div>
      <div class="modal-field">
        <span class="modal-label">Scope</span>
        <select bind:value={newTokenRole} class="modal-select">
          {#each roleOptions as r}
            <option value={r}>{r}</option>
          {/each}
        </select>
      </div>
      {#if tokenError}<div class="error">{tokenError}</div>{/if}
      <div class="modal-actions">
        <Button variant="secondary" onclick={() => { showNewTokenModal = false; tokenError = null; }}>Cancel</Button>
        <Button onclick={createApiToken}>Create</Button>
      </div>
    </div>
  {/snippet}
</Modal>

<Modal open={!!createdTokenSecret} title="Token Created" onclose={() => { createdTokenSecret = null; }}>
  {#snippet children()}
    <div class="modal-form">
      <p class="section-desc">Copy this token now. It will not be shown again.</p>
      <div class="token-secret">{createdTokenSecret}</div>
      <div class="modal-actions">
        <Button onclick={() => navigator.clipboard.writeText(createdTokenSecret!)}>Copy to clipboard</Button>
        <Button variant="secondary" onclick={() => { createdTokenSecret = null; }}>Done</Button>
      </div>
    </div>
  {/snippet}
</Modal>

<Modal open={showNewUserModal} title="New User" onclose={() => { showNewUserModal = false; userError = null; }}>
  {#snippet children()}
    <div class="modal-form">
      <div class="modal-field">
        <span class="modal-label">Username</span>
        <Input bind:value={newUserName} placeholder="username" />
      </div>
      <div class="modal-field">
        <span class="modal-label">Password (min 8 chars)</span>
        <Input type="password" bind:value={newUserPassword} />
      </div>
      <div class="modal-field">
        <span class="modal-label">Role</span>
        <select bind:value={newUserRole} class="modal-select">
          {#each ["ro", "normal", "admin"] as r}
            <option value={r}>{r}</option>
          {/each}
        </select>
      </div>
      {#if userError}<div class="error">{userError}</div>{/if}
      <div class="modal-actions">
        <Button variant="secondary" onclick={() => { showNewUserModal = false; userError = null; }}>Cancel</Button>
        <Button onclick={createUser}>Create user</Button>
      </div>
    </div>
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

  .subsection-title { margin: 0 0 var(--space-2); font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: .05em; }
  .tag-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: var(--space-2); }
  .tag { display: flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 10px; background: var(--surface-alt); border: 1px solid var(--border); font-size: 12px; color: var(--text-muted); }
  .tag-remove { border: none; background: none; color: var(--text-faint); cursor: pointer; font-size: 9px; padding: 0 2px; line-height: 1; }
  .tag-remove:hover { color: var(--danger); }
  .add-row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; margin-top: var(--space-2); }
  .add-row :global(.ui-input) { flex: 1; min-width: 120px; }

  .hidden-file-input { display: none; }

  .token-table { width: 100%; border-collapse: collapse; margin-top: var(--space-2); font-size: 0.875rem; }
  .token-table th { text-align: left; padding: 6px 8px; color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  .token-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); color: var(--text); }
  .role-badge { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px; font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }
  .section-desc { font-size: 0.875rem; color: var(--text-muted); margin: 0 0 var(--space-2); }
  .empty-hint { font-size: 0.875rem; color: var(--text-faint); margin: var(--space-2) 0 0; }

  .modal-form { display: flex; flex-direction: column; gap: 14px; }
  .modal-field { display: flex; flex-direction: column; gap: 5px; }
  .modal-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .modal-select { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; color: var(--text); font-size: 0.9rem; font-family: var(--font-sans); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
  .token-secret { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: var(--font-mono, monospace); font-size: 0.8rem; word-break: break-all; color: var(--text); }
  .inline-pw-input { background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; font-size: 0.85rem; color: var(--text); font-family: var(--font-sans); }

  .section-title { margin: 0 0 12px; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .home-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
  .home-label { font-size: 13px; color: var(--text-muted); width: 60px; flex-shrink: 0; }
  .home-value { font-size: 13px; font-weight: 500; color: var(--text); flex: 1; }
  .home-edit-row { display: flex; gap: 8px; flex: 1; align-items: center; }
  .danger-row { padding-top: 12px; margin-top: 4px; border-top: 1px solid var(--border); }

  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
  .module-group { margin-bottom: 16px; }
  .group-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin: 0 0 8px; display: flex; align-items: center; gap: 8px; }
  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-icon { font-size: 16px; width: 20px; text-align: center; }
  .mod-label { font-size: 13px; color: var(--text); }
  .soon-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; background: var(--surface-hover); color: var(--text-muted); border-radius: var(--radius-pill); padding: 1px 5px; }
  .field-error { color: var(--danger, #c0392b); font-size: 12px; margin: 4px 0 0; }
  .module-warning { font-size: 12px; color: var(--text-muted); background: var(--surface-hover); border-radius: var(--radius); padding: 8px 10px; margin: 0 0 8px; }
</style>
