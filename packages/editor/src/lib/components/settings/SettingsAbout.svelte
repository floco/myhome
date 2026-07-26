<!-- packages/editor/src/lib/components/settings/SettingsAbout.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Card from "../ui/Card.svelte";

  interface UpdateCheck {
    status: "up_to_date" | "update_available" | "unknown";
    latestVersion: string | null;
    checkedAt: string | null;
  }
  interface SystemInfo {
    version: string;
    deploymentMode: string;
    pythonVersion: string;
    arch: string;
    dbSchemaVersion: number;
    homeCount: number;
    databaseSizeBytes: number;
    uptimeSeconds: number;
    updateCheck: UpdateCheck;
  }

  let info = $state<SystemInfo | null>(null);
  let loadError = $state<string | null>(null);

  async function load(): Promise<void> {
    try {
      const resp = await fetch("/api/system/info");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      info = await resp.json();
    } catch {
      loadError = $_('settings.about.loadFailed');
    }
  }

  load();

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatUptime(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }
</script>

<Card>
  <div class="section-header">
    <h2>{$_('settings.nav.about')}</h2>
  </div>

  {#if loadError}
    <div class="error">{loadError}</div>
  {:else if info}
    <div class="version-headline">{$_('settings.about.appName')} v{info.version}</div>

    {#if info.updateCheck.status === "update_available"}
      <a
        class="update-status available"
        href="https://github.com/floco/myhome/tags"
        target="_blank"
        rel="noopener noreferrer"
      >
        {$_('settings.about.updateAvailable', { values: { version: info.updateCheck.latestVersion } })}
      </a>
    {:else if info.updateCheck.status === "up_to_date"}
      <div class="update-status uptodate">{$_('settings.about.upToDate')}</div>
    {:else}
      <div class="update-status unknown">{$_('settings.about.updateUnknown')}</div>
    {/if}

    <dl class="info-list">
      <div class="info-row">
        <dt>{$_('settings.about.deploymentMode')}</dt>
        <dd>{info.deploymentMode === "home_assistant" ? $_('settings.about.deploymentHa') : $_('settings.about.deploymentStandalone')}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.pythonVersion')}</dt>
        <dd>{info.pythonVersion}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.architecture')}</dt>
        <dd>{info.arch}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.dbSchemaVersion')}</dt>
        <dd>{info.dbSchemaVersion}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.homeCount')}</dt>
        <dd>{info.homeCount}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.databaseSize')}</dt>
        <dd>{formatBytes(info.databaseSizeBytes)}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.uptime')}</dt>
        <dd>{formatUptime(info.uptimeSeconds)}</dd>
      </div>
    </dl>
  {/if}
</Card>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  .version-headline { font-size: 20px; font-weight: 700; color: var(--text); margin: var(--space-2) 0; }

  .update-status { display: inline-block; font-size: 12px; padding: 4px 10px; border-radius: 999px; margin-bottom: var(--space-3); text-decoration: none; }
  .update-status.uptodate { background: color-mix(in srgb, var(--success) 15%, transparent); color: var(--success); }
  .update-status.available { background: color-mix(in srgb, var(--accent) 15%, transparent); color: var(--accent); cursor: pointer; }
  .update-status.unknown { background: var(--surface-hover); color: var(--text-faint); }

  .info-list { display: flex; flex-direction: column; gap: 8px; margin: 0; }
  .info-row { display: flex; justify-content: space-between; gap: var(--space-3); padding: 6px 0; border-bottom: 1px solid var(--border); }
  .info-row dt { font-size: 12px; color: var(--text-muted); }
  .info-row dd { margin: 0; font-size: 12px; color: var(--text); font-weight: 600; }
</style>
