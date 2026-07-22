<!-- packages/editor/src/lib/components/settings/SettingsIntegrations.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createAuthStore } from "../../authStore.svelte";
  import Card from "../ui/Card.svelte";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";

  type AuthStore = ReturnType<typeof createAuthStore>;

  interface Props {
    authStore: AuthStore;
    importFromDonetick: (token: string) => Promise<number>;
  }
  let { authStore, importFromDonetick }: Props = $props();

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

  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await importFromDonetick(importToken.trim());
      importStatus = "done";
      importToken = "";
    } catch {
      importStatus = "error";
    }
  }
</script>

{#if authStore.user?.role === "admin"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.integrations.mcpServer')}</h2>
    </div>
    <p class="section-desc">
      {$_('settings.integrations.mcpDesc')}
    </p>
    {#if mcpConfigLoaded}
      <label class="module-row">
        <input type="checkbox" checked={mcpEnabled} onchange={toggleMcpEnabled} />
        <span class="mod-label">{$_('settings.integrations.enableMcp')}</span>
      </label>
      {#if mcpEnabled}
        <p class="empty-hint">{$_('settings.integrations.connectionUrl')} <code>{window.location.origin}/mcp</code></p>
      {/if}
    {/if}
    {#if mcpError}<div class="error">{mcpError}</div>{/if}
  </Card>

  <Card>
    <div class="section-header">
      <h2>{$_('settings.integrations.donetick')}</h2>
    </div>
    <p class="section-desc">
      {$_('settings.integrations.donetickDesc')}
    </p>
    <div class="import-row">
      <Input type="password" placeholder={$_('settings.integrations.apiTokenPlaceholder')} bind:value={importToken} />
      <Button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? $_('settings.integrations.importing') : $_('settings.integrations.import')}
      </Button>
      {#if importStatus === "error"}<span class="msg-error">{$_('settings.integrations.failed')}</span>{/if}
      {#if importStatus === "done"}<span class="msg-success">{$_('settings.integrations.imported', { values: { n: importCount } })}</span>{/if}
    </div>
  </Card>
{/if}

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
  .empty-hint { font-size: 0.875rem; color: var(--text-faint); margin: var(--space-2) 0 0; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-label { font-size: 13px; color: var(--text); }

  .import-row { display: flex; align-items: center; gap: 10px; margin-top: var(--space-2); }
  .msg-error { color: var(--danger); font-size: 11px; }
  .msg-success { color: var(--success); font-size: 11px; }
</style>
