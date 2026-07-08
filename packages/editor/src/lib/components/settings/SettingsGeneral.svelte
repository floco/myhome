<!-- packages/editor/src/lib/components/settings/SettingsGeneral.svelte -->
<script lang="ts">
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";
  import Modal from "../ui/Modal.svelte";
  import { homesStore } from "../../homesStore.svelte";

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

<Modal open={showDeleteConfirm} title="Delete home" onclose={() => { showDeleteConfirm = false; }}>
  <p>Delete <strong>{homesStore.activeHome?.name}</strong>? This permanently removes all data for this home and cannot be undone.</p>
  {#if deleteError}<p class="field-error">{deleteError}</p>{/if}
  {#snippet footer()}
    <Button variant="ghost" onclick={() => { showDeleteConfirm = false; }}>Cancel</Button>
    <Button variant="danger" onclick={confirmDeleteHome}>Delete</Button>
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
</style>
