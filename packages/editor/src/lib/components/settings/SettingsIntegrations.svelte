<!-- packages/editor/src/lib/components/settings/SettingsIntegrations.svelte -->
<script lang="ts">
  import type { createAuthStore } from "../../authStore.svelte";
  import Card from "../ui/Card.svelte";

  type AuthStore = ReturnType<typeof createAuthStore>;

  interface Props {
    authStore: AuthStore;
  }
  let { authStore }: Props = $props();

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
</script>

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

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
  .empty-hint { font-size: 0.875rem; color: var(--text-faint); margin: var(--space-2) 0 0; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-label { font-size: 13px; color: var(--text); }
</style>
