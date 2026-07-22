<!-- packages/editor/src/lib/components/settings/SettingsActivityLog.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Input from "../ui/Input.svelte";
  import Button from "../ui/Button.svelte";
  import Card from "../ui/Card.svelte";
  import { homesStore } from "../../homesStore.svelte";

  interface ActivityEntry {
    id: string;
    timestamp: string;
    userId: string;
    username: string;
    module: string;
    action: string;
    entityLabel: string;
    refId: string | null;
    description: string;
  }

  const ACTIVITY_PAGE_SIZE = 50;
  let activityEntries = $state<ActivityEntry[]>([]);
  let activityTotal = $state(0);
  let activityLoaded = $state(false);
  let activityModuleFilter = $state("");
  let activityUserFilter = $state("");
  let activitySinceFilter = $state("");
  let activityUntilFilter = $state("");
  let activityOffset = $state(0);

  function buildActivityQuery(offset: number): string {
    const params = new URLSearchParams();
    if (activityModuleFilter) params.set("module", activityModuleFilter);
    if (activityUserFilter) params.set("userId", activityUserFilter);
    if (activitySinceFilter) params.set("since", activitySinceFilter);
    if (activityUntilFilter) params.set("until", `${activityUntilFilter}T23:59:59`);
    params.set("limit", String(ACTIVITY_PAGE_SIZE));
    params.set("offset", String(offset));
    return params.toString();
  }

  async function loadActivity(reset: boolean): Promise<void> {
    if (!homesStore.activeHomeId) { activityLoaded = true; return; }
    const offset = reset ? 0 : activityOffset;
    try {
      const resp = await fetch(`/api/homes/${homesStore.activeHomeId}/activity?${buildActivityQuery(offset)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      activityEntries = reset ? data.entries : [...activityEntries, ...data.entries];
      activityTotal = data.total;
      activityOffset = offset + data.entries.length;
    } finally {
      activityLoaded = true;
    }
  }

  function applyActivityFilters(): void {
    loadActivity(true);
  }

  function loadMoreActivity(): void {
    loadActivity(false);
  }

  loadActivity(true);
</script>

<Card>
    <div class="section-header">
      <h2>{$_('settings.nav.activity')}</h2>
    </div>
    <div class="modal-form">
      <div class="modal-field">
        <span class="modal-label">{$_('settings.activityLog.module')}</span>
        <select class="activity-module-filter modal-select" bind:value={activityModuleFilter} onchange={applyActivityFilters}>
          <option value="">{$_('settings.activityLog.allModules')}</option>
          <option value="chores">{$_('common.modules.chores')}</option>
          <option value="works">{$_('common.modules.works')}</option>
          <option value="costs">{$_('common.modules.costs')}</option>
          <option value="inventory">{$_('common.modules.inventory')}</option>
          <option value="consumables">{$_('common.modules.consumables')}</option>
          <option value="kb">{$_('common.modules.kb')}</option>
          <option value="locations">{$_('common.modules.locations')}</option>
          <option value="properties">{$_('common.modules.properties')}</option>
        </select>
      </div>
      <div class="modal-field">
        <span class="modal-label">{$_('settings.activityLog.from')}</span>
        <Input type="date" bind:value={activitySinceFilter} />
      </div>
      <div class="modal-field">
        <span class="modal-label">{$_('settings.activityLog.to')}</span>
        <Input type="date" bind:value={activityUntilFilter} />
      </div>
      <div class="modal-actions">
        <Button variant="secondary" onclick={applyActivityFilters}>{$_('settings.activityLog.filter')}</Button>
      </div>
    </div>
    {#if activityLoaded}
      {#if activityEntries.length === 0}
        <p class="empty-hint">{$_('settings.activityLog.noActivity')}</p>
      {:else}
        <table class="token-table">
          <thead>
            <tr><th>{$_('settings.activityLog.when')}</th><th>{$_('settings.activityLog.who')}</th><th>{$_('settings.activityLog.what')}</th></tr>
          </thead>
          <tbody>
            {#each activityEntries as entry (entry.id)}
              <tr>
                <td>{new Date(entry.timestamp).toLocaleString()}</td>
                <td>{entry.username}</td>
                <td>{entry.description}</td>
              </tr>
            {/each}
          </tbody>
        </table>
        {#if activityEntries.length < activityTotal}
          <Button variant="secondary" onclick={loadMoreActivity}>{$_('settings.activityLog.loadMore')}</Button>
        {/if}
      {/if}
    {/if}
  </Card>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .empty-hint { font-size: 0.875rem; color: var(--text-faint); margin: var(--space-2) 0 0; }

  .token-table { width: 100%; border-collapse: collapse; margin-top: var(--space-2); font-size: 0.875rem; }
  .token-table th { text-align: left; padding: 6px 8px; color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  .token-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); color: var(--text); }

  .modal-form { display: flex; flex-direction: column; gap: 14px; }
  .modal-field { display: flex; flex-direction: column; gap: 5px; }
  .modal-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .modal-select { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; color: var(--text); font-size: 0.9rem; font-family: var(--font-sans); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
</style>
