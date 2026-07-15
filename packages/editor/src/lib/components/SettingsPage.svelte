<!-- packages/editor/src/lib/components/SettingsPage.svelte -->
<script lang="ts">
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createAuthStore } from "../authStore.svelte";
  import SettingsNav from "./settings/SettingsNav.svelte";
  import SettingsGeneral from "./settings/SettingsGeneral.svelte";
  import SettingsCategories from "./settings/SettingsCategories.svelte";
  import SettingsNotifications from "./settings/SettingsNotifications.svelte";
  import SettingsSecurity from "./settings/SettingsSecurity.svelte";
  import SettingsIntegrations from "./settings/SettingsIntegrations.svelte";
  import SettingsBackup from "./settings/SettingsBackup.svelte";
  import SettingsActivityLog from "./settings/SettingsActivityLog.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type AuthStore = ReturnType<typeof createAuthStore>;

  interface Props {
    store: SettingsStore;
    authStore: AuthStore;
    importFromDonetick: (token: string) => Promise<number>;
  }
  let { store, authStore, importFromDonetick }: Props = $props();

  interface SettingsGroupDef {
    id: string;
    icon: string;
    label: string;
    adminOnly?: boolean;
  }

  const ALL_GROUPS: SettingsGroupDef[] = [
    { id: "general", icon: "⚙️", label: "General" },
    { id: "categories", icon: "🏷️", label: "Categories" },
    { id: "notifications", icon: "🔔", label: "Notifications" },
    { id: "security", icon: "🔐", label: "Security & Access" },
    { id: "integrations", icon: "🔌", label: "Integrations", adminOnly: true },
    { id: "backup", icon: "💾", label: "Backup & Restore" },
    { id: "activity", icon: "📜", label: "Activity Log" },
  ];

  const visibleGroups = $derived(
    ALL_GROUPS.filter((g) => !g.adminOnly || authStore.user?.role === "admin"),
  );

  let activeGroup = $state("general");
</script>

<div class="page">
  <div class="page-header">
    <h1>Settings</h1>
  </div>

  <div class="body">
    <SettingsNav
      groups={visibleGroups}
      active={activeGroup}
      onchange={(id) => { activeGroup = id; }}
    />

    <div class="content">
      {#if activeGroup === "general"}
        <SettingsGeneral />
      {:else if activeGroup === "categories"}
        <SettingsCategories {store} />
      {:else if activeGroup === "notifications"}
        <SettingsNotifications {store} />
      {:else if activeGroup === "security"}
        <SettingsSecurity {authStore} />
      {:else if activeGroup === "integrations"}
        <SettingsIntegrations {authStore} {importFromDonetick} />
      {:else if activeGroup === "backup"}
        <SettingsBackup />
      {:else if activeGroup === "activity"}
        <SettingsActivityLog />
      {/if}
    </div>
  </div>
</div>

<style>
  .page {
    display: flex; flex-direction: column; height: 100%;
    background: var(--bg); font-family: var(--font-sans); overflow: hidden;
  }
  .page-header {
    padding: var(--space-4) var(--space-4) var(--space-2); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  h1 { margin: 0; font-size: 16px; color: var(--text); font-weight: 600; }
  .body { display: flex; flex: 1; min-height: 0; }
  .content { flex: 1; overflow-y: auto; padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-5); }

  @media (max-width: 720px) {
    .body { flex-direction: column; }
  }
</style>
