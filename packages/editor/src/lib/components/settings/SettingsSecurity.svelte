<!-- packages/editor/src/lib/components/settings/SettingsSecurity.svelte -->
<script lang="ts">
  import type { createAuthStore } from "../../authStore.svelte";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";
  import Modal from "../ui/Modal.svelte";
  import SortableTable from "../ui/SortableTable.svelte";
  import type { Column } from "../ui/SortableTable.types";

  type AuthStore = ReturnType<typeof createAuthStore>;

  interface Props {
    authStore: AuthStore;
  }
  let { authStore }: Props = $props();

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
</script>

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
      {#snippet tokenNameCell(t: TokenInfo)}{t.name}{/snippet}
      {#snippet tokenScopeCell(t: TokenInfo)}<span class="role-badge">{t.role}</span>{/snippet}
      {#snippet tokenCreatedCell(t: TokenInfo)}{t.created_at?.slice(0, 10) ?? "—"}{/snippet}
      {#snippet tokenLastUsedCell(t: TokenInfo)}{t.last_used_at ? t.last_used_at.slice(0, 10) : "—"}{/snippet}
      {#snippet tokenActionsCell(t: TokenInfo)}
        {#if confirmRevokeTokenId === t.id}
          <Button variant="danger" onclick={() => revokeToken(t.id)}>Confirm revoke</Button>
          <Button variant="secondary" onclick={() => { confirmRevokeTokenId = null; }}>Cancel</Button>
        {:else}
          <Button variant="secondary" onclick={() => { confirmRevokeTokenId = t.id; }}>Revoke</Button>
        {/if}
      {/snippet}
      <SortableTable
        class="token-table"
        columns={[
          { key: "name", label: "Name", sortValue: (t) => t.name, cell: tokenNameCell },
          { key: "scope", label: "Scope", sortValue: (t) => t.role, cell: tokenScopeCell },
          { key: "created", label: "Created", sortValue: (t) => (t.created_at ? new Date(t.created_at) : null), cell: tokenCreatedCell },
          { key: "lastUsed", label: "Last used", sortValue: (t) => (t.last_used_at ? new Date(t.last_used_at) : null), cell: tokenLastUsedCell },
          { key: "actions", label: "", sortable: false, cell: tokenActionsCell },
        ] as Column<TokenInfo>[]}
        rows={apiTokens}
        rowKey={(t) => t.id}
      />
    {/if}
  {/if}
</Card>

{#if authStore.user?.role === "admin"}
  <Card>
    <div class="section-header">
      <h2>Users</h2>
      <Button onclick={() => { showNewUserModal = true; userError = null; }}>New user</Button>
    </div>
    {#if usersLoaded}
      {#snippet userNameCell(u: UserInfo)}{u.username}{/snippet}
      {#snippet userRoleCell(u: UserInfo)}
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
      {/snippet}
      {#snippet userCreatedCell(u: UserInfo)}{u.created_at?.slice(0, 10) ?? "—"}{/snippet}
      {#snippet userActionsCell(u: UserInfo)}
        <div style="display:flex;gap:4px;flex-wrap:wrap">
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
        </div>
      {/snippet}
      <SortableTable
        class="token-table"
        columns={[
          { key: "username", label: "Username", sortValue: (u) => u.username, cell: userNameCell },
          { key: "role", label: "Role", sortValue: (u) => u.role, cell: userRoleCell },
          { key: "created", label: "Created", sortValue: (u) => (u.created_at ? new Date(u.created_at) : null), cell: userCreatedCell },
          { key: "actions", label: "Actions", sortable: false, cell: userActionsCell },
        ] as Column<UserInfo>[]}
        rows={users}
        rowKey={(u) => u.id}
      />
    {/if}
  </Card>
{/if}

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
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
  .empty-hint { font-size: 0.875rem; color: var(--text-faint); margin: var(--space-2) 0 0; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  :global(table.token-table) { margin-top: var(--space-2); font-size: 0.875rem; }
  :global(table.token-table td) { color: var(--text); }
  .role-badge { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px; font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }

  .modal-form { display: flex; flex-direction: column; gap: 14px; }
  .modal-field { display: flex; flex-direction: column; gap: 5px; }
  .modal-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .modal-select { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; color: var(--text); font-size: 0.9rem; font-family: var(--font-sans); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
  .token-secret { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: var(--font-mono, monospace); font-size: 0.8rem; word-break: break-all; color: var(--text); }
  .inline-pw-input { background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; font-size: 0.85rem; color: var(--text); font-family: var(--font-sans); }

  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-label { font-size: 13px; color: var(--text); }
</style>
