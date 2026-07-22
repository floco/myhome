<!-- packages/editor/src/lib/components/settings/SettingsGeneral.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";
  import Modal from "../ui/Modal.svelte";
  import { homesStore } from "../../homesStore.svelte";
  import { getStoredLocale, setLocale, type Locale } from "../../locale";

  let currentLocale = $state<Locale>(getStoredLocale());

  function changeLocale(next: Locale): void {
    currentLocale = next;
    setLocale(next);
  }

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
    if (!homeNameDraft.trim()) { homeNameError = $_('settings.general.nameRequired'); return; }
    const id = homesStore.activeHomeId;
    if (!id) return;
    try {
      await homesStore.patchHome(id, { name: homeNameDraft.trim() });
      editingHomeName = false;
    } catch (e) {
      homeNameError = e instanceof Error ? e.message : $_('settings.general.failedToSave');
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
      homeTypeError = e instanceof Error ? e.message : $_('settings.general.failedToUpdateType');
    }
  }

  let moduleToggleWarning = $state<string | null>(null);

  async function toggleModule(moduleId: string): Promise<void> {
    const home = homesStore.activeHome;
    if (!home) return;
    const current = home.enabledModules;
    const isDisabling = current.includes(moduleId);
    if (isDisabling) {
      moduleToggleWarning = $_('settings.general.moduleHideWarning', { values: { label: $_(`common.modules.${moduleId}`) } });
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
      deleteError = e instanceof Error ? e.message : $_('settings.general.failedToDelete');
    }
  }

  const CORE_MODULES = [
    { id: "home",        icon: "🏡" },
    { id: "plan",        icon: "📐" },
    { id: "chores",      icon: "✅" },
    { id: "inventory",   icon: "📦" },
    { id: "consumables", icon: "🛒" },
    { id: "works",       icon: "🔧" },
    { id: "kb",          icon: "📖" },
    { id: "costs",       icon: "💶" },
  ];

  const PROJECT_MODULES = [
    { id: "locations",  icon: "🌍" },
    { id: "properties", icon: "🏘" },
    { id: "budget",     icon: "💰" },
    { id: "visits",     icon: "📅" },
    { id: "contacts",   icon: "👤" },
    { id: "checklist",  icon: "✅" },
  ];
</script>

<Card>
  <h2 class="section-title">{$_('settings.general.home')}</h2>

  <div class="home-row">
    <span class="home-label">{$_('settings.general.name')}</span>
    {#if editingHomeName}
      <div class="home-edit-row">
        <Input bind:value={homeNameDraft} placeholder={$_('settings.general.homeNamePlaceholder')} />
        <Button onclick={saveHomeName}>{$_('common.save')}</Button>
        <Button variant="ghost" onclick={() => { editingHomeName = false; }}>{$_('common.cancel')}</Button>
      </div>
      {#if homeNameError}<p class="field-error">{homeNameError}</p>{/if}
    {:else}
      <span class="home-value">{homesStore.activeHome?.name ?? "—"}</span>
      <Button variant="ghost" onclick={startEditHomeName}>{$_('common.edit')}</Button>
    {/if}
  </div>

  <div class="home-row">
    <span class="home-label">{$_('settings.general.type')}</span>
    <span class="home-value">
      {homesStore.activeHome?.type === "project" ? $_('settings.general.projectHome') : $_('settings.general.existingHome')}
    </span>
    <Button variant="ghost" onclick={toggleHomeType}>{$_('settings.general.change')}</Button>
  </div>
  {#if homeTypeError}<p class="field-error">{homeTypeError}</p>{/if}

  <div class="home-row danger-row">
    <Button
      variant="danger"
      disabled={homesStore.homes.length <= 1}
      onclick={() => { showDeleteConfirm = true; }}
      title={homesStore.homes.length <= 1 ? $_('settings.general.cannotDeleteOnlyHome') : undefined}
    >
      {$_('settings.general.deleteThisHome')}
    </Button>
  </div>
</Card>

<Card>
  <h2 class="section-title">{$_('settings.general.language')}</h2>
  <div class="home-row">
    <span class="home-label">{$_('settings.general.language')}</span>
    <select class="lang-select" value={currentLocale} onchange={(e) => changeLocale((e.target as HTMLSelectElement).value as Locale)}>
      <option value="en">English</option>
      <option value="fr">Français</option>
    </select>
  </div>
</Card>

<Card>
  <h2 class="section-title">{$_('settings.general.modules')}</h2>
  <p class="section-desc">{$_('settings.general.modulesDesc')}</p>

  {#if moduleToggleWarning}
    <p class="module-warning">{moduleToggleWarning}</p>
  {/if}

  <div class="module-group">
    <h3 class="group-label">{$_('settings.general.coreModules')}</h3>
    {#each CORE_MODULES as mod (mod.id)}
      <label class="module-row">
        <input
          type="checkbox"
          checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
          onchange={() => toggleModule(mod.id)}
        />
        <span class="mod-icon">{mod.icon}</span>
        <span class="mod-label">{$_(`common.modules.${mod.id}`)}</span>
      </label>
    {/each}
  </div>

  <div class="module-group">
    <h3 class="group-label">{$_('settings.general.projectModules')} <span class="soon-tag">{$_('settings.general.placeholderTag')}</span></h3>
    {#each PROJECT_MODULES as mod (mod.id)}
      <label class="module-row">
        <input
          type="checkbox"
          checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
          onchange={() => toggleModule(mod.id)}
        />
        <span class="mod-icon">{mod.icon}</span>
        <span class="mod-label">{$_(`common.modules.${mod.id}`)}</span>
      </label>
    {/each}
  </div>
</Card>

<Modal open={showDeleteConfirm} title={$_('settings.general.deleteHomeTitle')} onclose={() => { showDeleteConfirm = false; }}>
  <p>{$_('settings.general.deleteHomePrefix')} <strong>{homesStore.activeHome?.name}</strong>{$_('settings.general.deleteHomeSuffix')}</p>
  {#if deleteError}<p class="field-error">{deleteError}</p>{/if}
  {#snippet footer()}
    <Button variant="ghost" onclick={() => { showDeleteConfirm = false; }}>{$_('common.cancel')}</Button>
    <Button variant="danger" onclick={confirmDeleteHome}>{$_('common.delete')}</Button>
  {/snippet}
</Modal>

<style>
  .section-title { margin: 0 0 12px; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .home-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
  .home-label { font-size: 13px; color: var(--text-muted); width: 60px; flex-shrink: 0; }
  .home-value { font-size: 13px; font-weight: 500; color: var(--text); flex: 1; }
  .home-edit-row { display: flex; gap: 8px; flex: 1; align-items: center; }
  .danger-row { padding-top: 12px; margin-top: 4px; border-top: 1px solid var(--border); }
  .field-error { color: var(--danger, #c0392b); font-size: 12px; margin: 4px 0 0; }

  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
  .module-group { margin-bottom: 16px; }
  .group-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin: 0 0 8px; display: flex; align-items: center; gap: 8px; }
  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-icon { font-size: 16px; width: 20px; text-align: center; }
  .mod-label { font-size: 13px; color: var(--text); }
  .soon-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; background: var(--surface-hover); color: var(--text-muted); border-radius: var(--radius-pill); padding: 1px 5px; }
  .module-warning { font-size: 12px; color: var(--text-muted); background: var(--surface-hover); border-radius: var(--radius); padding: 8px 10px; margin: 0 0 8px; }
  .lang-select { font-size: 13px; padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--surface); color: var(--text); }
</style>
