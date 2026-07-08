# Settings Page Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single 1839-line, 14-section `SettingsPage.svelte` with a sidebar-navigated Settings page: a thin shell + 7 focused panel components grouped as General / Categories / Notifications / Security & Access / Integrations / Backup & Restore / Activity Log.

**Architecture:** Extract each group's existing script/markup/style into its own component under `packages/editor/src/lib/components/settings/`, each getting its own test file. Only after every panel is built and independently tested does `SettingsPage.svelte` get rewritten into a thin shell (new `SettingsNav.svelte` + conditional panel rendering) and `SettingsPage.test.ts` rewritten to a slim nav/wiring test. This keeps the existing monolith working (and its test suite green) throughout extraction, with one clean cutover at the end.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest (`mount`/`unmount`/`flushSync` from `"svelte"`), existing shared UI kit (`Button`, `Input`, `Card`, `Modal`, `EmojiPicker`, `Tabs`).

**Reference spec:** `docs/superpowers/specs/2026-07-08-settings-reorganization-design.md`

**Important CSS note discovered during planning:** the current single stylesheet in `SettingsPage.svelte` defines `.section-desc` twice (once at "0.875rem" sizing, once at "13px / margin 12px"). Because both are plain single-class selectors in one stylesheet, the later rule (13px / margin 12px) wins everywhere on the page today, and the 0.875rem rule is fully dead. Every extracted panel below uses the 13px/12px version to preserve current visual behavior exactly.

---

### Task 1: Create `SettingsNav.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsNav.svelte`
- Test: `packages/editor/test/SettingsNav.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsNav.test.ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsNav from "../src/lib/components/settings/SettingsNav.svelte";

const GROUPS = [
  { id: "general", icon: "⚙️", label: "General" },
  { id: "categories", icon: "🏷️", label: "Categories" },
  { id: "security", icon: "🔐", label: "Security & Access" },
];

describe("SettingsNav", () => {
  it("renders a nav button for each group", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange: vi.fn() } });
    flushSync();
    expect(target.querySelectorAll(".nav-item").length).toBe(3);
    expect(target.textContent).toContain("Categories");
    unmount(app);
  });

  it("marks the active group's button with the active class", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "categories", onchange: vi.fn() } });
    flushSync();
    const active = target.querySelector(".nav-item.active");
    expect(active?.textContent).toContain("Categories");
    unmount(app);
  });

  it("calls onchange with the clicked group's id", () => {
    const target = document.createElement("div");
    const onchange = vi.fn();
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange } });
    flushSync();
    const buttons = [...target.querySelectorAll<HTMLButtonElement>(".nav-item")];
    const securityBtn = buttons.find((b) => b.textContent?.includes("Security & Access"))!;
    securityBtn.click();
    expect(onchange).toHaveBeenCalledWith("security");
    unmount(app);
  });

  it("renders a select dropdown with matching options for mobile", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange: vi.fn() } });
    flushSync();
    const select = target.querySelector(".nav-select") as HTMLSelectElement;
    expect(select).not.toBeNull();
    const values = [...select.querySelectorAll("option")].map((o) => o.value);
    expect(values).toEqual(["general", "categories", "security"]);
    unmount(app);
  });

  it("calls onchange when the dropdown value changes", () => {
    const target = document.createElement("div");
    const onchange = vi.fn();
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange } });
    flushSync();
    const select = target.querySelector(".nav-select") as HTMLSelectElement;
    select.value = "categories";
    select.dispatchEvent(new Event("change"));
    expect(onchange).toHaveBeenCalledWith("categories");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsNav.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsNav.svelte`

- [ ] **Step 3: Create the component**

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsNav.svelte -->
<script lang="ts">
  interface SettingsGroup {
    id: string;
    icon: string;
    label: string;
  }

  interface Props {
    groups: SettingsGroup[];
    active: string;
    onchange: (id: string) => void;
  }
  let { groups, active, onchange }: Props = $props();
</script>

<nav class="settings-nav">
  {#each groups as group (group.id)}
    <button
      class="nav-item"
      class:active={group.id === active}
      onclick={() => onchange(group.id)}
    >
      <span class="nav-icon">{group.icon}</span>
      <span class="nav-label">{group.label}</span>
    </button>
  {/each}
</nav>

<div class="settings-nav-mobile">
  <select
    class="nav-select"
    value={active}
    onchange={(e) => onchange((e.target as HTMLSelectElement).value)}
  >
    {#each groups as group (group.id)}
      <option value={group.id}>{group.icon} {group.label}</option>
    {/each}
  </select>
</div>

<style>
  .settings-nav {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 200px;
    flex-shrink: 0;
    padding: var(--space-3);
    border-right: 1px solid var(--border);
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-radius: var(--radius);
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 13px;
    font-family: var(--font-sans);
    text-align: left;
    cursor: pointer;
  }
  .nav-item:hover { background: var(--surface-hover); color: var(--text); }
  .nav-item.active { background: var(--surface-alt); color: var(--text); font-weight: 600; }
  .nav-icon { font-size: 15px; width: 18px; text-align: center; }
  .settings-nav-mobile { display: none; }
  .nav-select {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 10px;
    color: var(--text);
    font-size: 13px;
    font-family: var(--font-sans);
  }

  @media (max-width: 720px) {
    .settings-nav { display: none; }
    .settings-nav-mobile { display: block; padding: var(--space-3); border-bottom: 1px solid var(--border); }
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsNav.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsNav.svelte packages/editor/test/SettingsNav.test.ts
git commit -m "feat: add SettingsNav sidebar/dropdown component"
```

---

### Task 2: Extract `SettingsGeneral.svelte` (Home + Modules)

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsGeneral.svelte`
- Test: `packages/editor/test/SettingsGeneral.test.ts`
- Reference (unchanged for now): `packages/editor/src/lib/components/SettingsPage.svelte:781-865` (script), `:876-963` (markup)

This panel takes **no props** — the Home/Modules logic only reads/writes `homesStore`, never `store` or `authStore`.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsGeneral.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsGeneral from "../src/lib/components/settings/SettingsGeneral.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function seedHome(overrides: Partial<{ id: string; name: string; type: "existing" | "project"; enabledModules: string[] }> = {}) {
  const home = {
    id: "h1", name: "Rue des Lilas", type: "existing" as const,
    enabledModules: ["home", "plan"], createdAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
  homesStore.homes.push(home);
  homesStore.setActiveHomeId(home.id);
  return home;
}

describe("SettingsGeneral", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    homesStore._reset();
  });

  it("renders the home name and type", () => {
    seedHome();
    const target = document.createElement("div");
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    expect(target.textContent).toContain("Rue des Lilas");
    expect(target.textContent).toContain("Existing home");
    unmount(app);
  });

  it("renders core module checkboxes reflecting enabledModules", () => {
    seedHome({ enabledModules: ["home", "plan", "chores"] });
    const target = document.createElement("div");
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    expect((choresRow.querySelector("input") as HTMLInputElement).checked).toBe(true);
    const worksRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Works"))!;
    expect((worksRow.querySelector("input") as HTMLInputElement).checked).toBe(false);
    unmount(app);
  });

  it("toggling a module checkbox calls patchHome with a PATCH request", async () => {
    seedHome({ enabledModules: ["home"] });
    vi.stubGlobal("fetch", makeFetch(200, { id: "h1", name: "Rue des Lilas", type: "existing", enabledModules: ["home", "chores"], createdAt: "2026-01-01T00:00:00Z" }));
    const target = document.createElement("div");
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    (choresRow.querySelector("input") as HTMLInputElement).click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetch).toHaveBeenCalledWith("/api/homes/h1", expect.objectContaining({ method: "PATCH" }));
    unmount(app);
  });

  it("editing the home name saves via patchHome", async () => {
    seedHome();
    vi.stubGlobal("fetch", makeFetch(200, { id: "h1", name: "New Name", type: "existing", enabledModules: ["home", "plan"], createdAt: "2026-01-01T00:00:00Z" }));
    const target = document.createElement("div");
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const editBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Edit")!;
    editBtn.click();
    flushSync();
    const input = target.querySelector("input.ui-input") as HTMLInputElement;
    input.value = "New Name";
    input.dispatchEvent(new Event("input"));
    flushSync();
    const saveBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Save")!;
    saveBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetch).toHaveBeenCalledWith("/api/homes/h1", expect.objectContaining({ method: "PATCH" }));
    unmount(app);
  });

  it("shows a delete confirmation modal and calls deleteHome on confirm", async () => {
    seedHome();
    homesStore.homes.push({ id: "h2", name: "Second", type: "existing", enabledModules: [], createdAt: "" });
    vi.stubGlobal("fetch", makeFetch(204));
    const target = document.createElement("div");
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const deleteBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("Delete this home"))!;
    deleteBtn.click();
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    const confirmBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.trim() === "Delete")!;
    confirmBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetch).toHaveBeenCalledWith("/api/homes/h1", expect.objectContaining({ method: "DELETE" }));
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsGeneral.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsGeneral.svelte`

- [ ] **Step 3: Create the component**

```svelte
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsGeneral.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsGeneral.svelte packages/editor/test/SettingsGeneral.test.ts
git commit -m "feat: extract SettingsGeneral panel (Home + Modules)"
```

---

### Task 3: Extract `SettingsCategories.svelte` (Cost/Inventory/Work/Suppliers/Consumables)

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsCategories.svelte`
- Test: `packages/editor/test/SettingsCategories.test.ts`
- Reference (unchanged for now): `SettingsPage.svelte:20-255` (script), `:966-1268` (markup)

Takes one prop: `store: SettingsStore`. Adds new `activeTab` state and renders `Tabs.svelte` so only one subsection shows at a time (per spec).

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsCategories.test.ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsCategories from "../src/lib/components/settings/SettingsCategories.svelte";

function makeStore() {
  return {
    costCategories: [{ id: "c1", name: "Electricity", emoji: "⚡", unit: "kWh", color: "#4466cc" }],
    inventoryCategories: [{ id: "i1", name: "Tools" }],
    workCategories: [{ id: "w1", name: "Plumbing", emoji: "🔧" }],
    suppliers: [{ id: "s1", name: "Acme Co" }],
    consumableUnits: ["tablets"],
    consumableCategories: [{ id: "cc1", name: "Cleaning", emoji: "🧼" }],
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
  };
}

describe("SettingsCategories", () => {
  it("shows the Cost categories tab by default", () => {
    const target = document.createElement("div");
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    expect(target.textContent).toContain("Cost categories");
    expect(target.textContent).toContain("Electricity");
    expect(target.textContent).not.toContain("Tools");
    unmount(app);
  });

  it("switches to the Inventory categories tab", () => {
    const target = document.createElement("div");
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Inventory categories")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("Tools");
    expect(target.textContent).not.toContain("Electricity");
    unmount(app);
  });

  it("adding a cost category calls store.updateCostCategories", async () => {
    const store = makeStore();
    const target = document.createElement("div");
    const app = mount(SettingsCategories, { target, props: { store } });
    flushSync();
    const addBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("＋ Add"))!;
    addBtn.click();
    flushSync();
    const nameInput = target.querySelector('input[placeholder="Name *"]') as HTMLInputElement;
    nameInput.value = "Water";
    nameInput.dispatchEvent(new Event("input"));
    flushSync();
    const okBtn = target.querySelector(".icon-action.ok") as HTMLButtonElement;
    okBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(store.updateCostCategories).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ name: "Water" })]),
    );
    unmount(app);
  });

  it("switches to the Consumables tab and shows units and categories", () => {
    const target = document.createElement("div");
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Consumables")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("tablets");
    expect(target.textContent).toContain("Cleaning");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsCategories.svelte`

- [ ] **Step 3: Create the component**

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsCategories.svelte -->
<script lang="ts">
  import type { createSettingsStore, CostCategory, ConsumableCategory, InventoryCategory, WorkCategory, Supplier } from "../../settingsStore.svelte";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import EmojiPicker from "../ui/EmojiPicker.svelte";
  import Card from "../ui/Card.svelte";
  import Tabs from "../ui/Tabs.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: SettingsStore;
  }
  let { store }: Props = $props();

  type CategoryTab = "cost" | "inventory" | "work" | "suppliers" | "consumables";
  let activeTab = $state<CategoryTab>("cost");

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
</script>

<Tabs
  tabs={[
    { id: "cost", label: "Cost categories" },
    { id: "inventory", label: "Inventory categories" },
    { id: "work", label: "Work categories" },
    { id: "suppliers", label: "Suppliers" },
    { id: "consumables", label: "Consumables" },
  ]}
  active={activeTab}
  onchange={(id) => { activeTab = id as CategoryTab; }}
/>

{#if activeTab === "cost"}
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
{/if}

{#if activeTab === "inventory"}
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
{/if}

{#if activeTab === "work"}
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
{/if}

{#if activeTab === "suppliers"}
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
{/if}

{#if activeTab === "consumables"}
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
{/if}

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }

  .table-wrapper { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { background: var(--surface-alt); }
  th { padding: 5px 10px; color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: .05em; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); }
  .editing-row td { background: var(--surface-alt); }

  .color-swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
  .emoji-cell { font-size: 15px; }
  .unit-cell { color: var(--text-faint); }

  .color-input { width: 36px; height: 24px; border: 1px solid var(--border); border-radius: 3px; padding: 0; cursor: pointer; background: none; }
  .name-cell-input :global(.ui-input) { width: 160px; }
  .name-cell-input.wide :global(.ui-input) { width: 260px; }
  .unit-cell-input :global(.ui-input) { width: 100px; }

  .actions { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
  .icon-action { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; padding: 2px 5px; border-radius: 3px; }
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
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsCategories.svelte packages/editor/test/SettingsCategories.test.ts
git commit -m "feat: extract SettingsCategories panel with sub-tabs"
```

---

### Task 4: Extract `SettingsNotifications.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsNotifications.svelte`
- Test: `packages/editor/test/SettingsNotifications.test.ts`
- Reference (unchanged for now): `SettingsPage.svelte:257-289` (script), `:1271-1313` (markup)

Takes one prop: `store: SettingsStore`.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsNotifications.test.ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsNotifications from "../src/lib/components/settings/SettingsNotifications.svelte";

function makeStore() {
  return {
    notificationSettings: {
      enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
      haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
    },
    loaded: true,
    updateNotificationSettings: vi.fn(),
  };
}

describe("SettingsNotifications", () => {
  it("renders current settings and reflects the enabled toggle", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNotifications, { target, props: { store: makeStore() } });
    flushSync();
    const heading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Notifications");
    expect(heading).toBeDefined();
    expect((target.querySelector(".notif-enable-toggle") as HTMLInputElement).checked).toBe(true);
    unmount(app);
  });

  it("hides push fields until 'Send a daily digest' is checked", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNotifications, { target, props: { store: makeStore() } });
    flushSync();
    const labels = Array.from(target.querySelectorAll(".modal-label")).map((el) => el.textContent);
    expect(labels).not.toContain("HA notify service");
    unmount(app);
  });

  it("saves edited settings via store.updateNotificationSettings", async () => {
    const store = makeStore();
    const target = document.createElement("div");
    const app = mount(SettingsNotifications, { target, props: { store } });
    flushSync();
    const enableToggle = target.querySelector(".notif-enable-toggle") as HTMLInputElement;
    enableToggle.click();
    enableToggle.click();
    flushSync();
    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Save"))!;
    (saveBtn as HTMLButtonElement).click();
    await Promise.resolve();
    expect(store.updateNotificationSettings).toHaveBeenCalledWith(
      expect.objectContaining({ enabled: true, warrantyDaysThreshold: 30 }),
    );
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsNotifications.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsNotifications.svelte`

- [ ] **Step 3: Create the component**

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsNotifications.svelte -->
<script lang="ts">
  import type { createSettingsStore } from "../../settingsStore.svelte";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: SettingsStore;
  }
  let { store }: Props = $props();

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
</script>

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

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-label { font-size: 13px; color: var(--text); }

  .modal-form { display: flex; flex-direction: column; gap: 14px; }
  .modal-field { display: flex; flex-direction: column; gap: 5px; }
  .modal-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsNotifications.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsNotifications.svelte packages/editor/test/SettingsNotifications.test.ts
git commit -m "feat: extract SettingsNotifications panel"
```

---

### Task 5: Extract `SettingsSecurity.svelte` (API Tokens + Users + SSO)

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsSecurity.svelte`
- Test: `packages/editor/test/SettingsSecurity.test.ts`
- Reference (unchanged for now): `SettingsPage.svelte:291-430` and `:463-524` (script), `:1316-1414` and `:1441-1492` (markup), `:1676-1739` (modals)

Takes one prop: `authStore: AuthStore`.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsSecurity.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsSecurity from "../src/lib/components/settings/SettingsSecurity.svelte";

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

function defaultOidcConfig() {
  return {
    enabled: false, provider_name: "", issuer: "", client_id: "",
    client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"],
  };
}

describe("SettingsSecurity", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  function setupFetch(overrides: Record<string, () => Promise<unknown>> = {}) {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      const key = `${opts?.method ?? "GET"} ${url}`;
      if (overrides[key]) return overrides[key]();
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  }

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    setupFetch();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders API Tokens, Users, and Single Sign-On for an admin", async () => {
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("API Tokens");
    expect(target.textContent).toContain("Users");
    expect(target.textContent).toContain("Single Sign-On");
    unmount(app);
  });

  it("hides Users and Single Sign-On for a non-admin but keeps API Tokens", async () => {
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("normal") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("API Tokens");
    expect(target.textContent).not.toContain("Single Sign-On");
    const cards = [...target.querySelectorAll(".ui-card")].map((c) => c.textContent);
    expect(cards.some((t) => t?.includes("New user"))).toBe(false);
    unmount(app);
  });

  it("creates an API token via POST /api/auth/tokens", async () => {
    setupFetch({
      "POST /api/auth/tokens": async () => ({
        ok: true,
        json: async () => ({ token: "abc123", info: { id: "t2", name: "Test", role: "ro", owner_id: "u1", created_at: "2026-07-02T11:00:00+00:00", last_used_at: null } }),
      }),
    });
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    flushSync();
    const newBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New token"))!;
    newBtn.click();
    flushSync();
    const nameInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    nameInput.value = "Test";
    nameInput.dispatchEvent(new Event("input"));
    flushSync();
    const createBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.trim() === "Create")!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    const postCalls = fetchMock.mock.calls.filter(
      ([url, opts]: [string, RequestInit | undefined]) => url === "/api/auth/tokens" && opts?.method === "POST",
    );
    expect(postCalls.length).toBe(1);
    unmount(app);
  });

  it("creates a user via POST /api/auth/users", async () => {
    setupFetch({
      "POST /api/auth/users": async () => ({
        ok: true,
        json: async () => ({ id: "u3", username: "bob", role: "normal", created_at: "2026-07-02T00:00:00+00:00" }),
      }),
    });
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New user"))!;
    btn.click();
    flushSync();
    const inputs = target.querySelectorAll(".ui-modal input");
    (inputs[0] as HTMLInputElement).value = "bob";
    inputs[0].dispatchEvent(new Event("input"));
    (inputs[1] as HTMLInputElement).value = "bobpassword1";
    inputs[1].dispatchEvent(new Event("input"));
    flushSync();
    const createBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.includes("Create user"))!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const postCalls = fetchMock.mock.calls.filter(
      ([url, opts]: [string, RequestInit | undefined]) => url === "/api/auth/users" && opts?.method === "POST",
    );
    expect(postCalls.length).toBe(1);
    unmount(app);
  });

  it("saves SSO config via PUT /api/auth/oidc/config", async () => {
    setupFetch({
      "PUT /api/auth/oidc/config": async () => ({
        ok: true,
        json: async () => ({ ...defaultOidcConfig(), enabled: true, provider_name: "Keycloak" }),
      }),
    });
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const ssoHeading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Single Sign-On")!;
    const ssoCard = ssoHeading.closest(".ui-card") as HTMLElement;
    const saveButtons = Array.from(ssoCard.querySelectorAll("button")).filter((b) => b.textContent?.trim() === "Save");
    saveButtons[saveButtons.length - 1].click();
    await new Promise((r) => setTimeout(r, 0));
    const putCall = fetchMock.mock.calls.find(
      (c: unknown[]) => c[0] === "/api/auth/oidc/config" && (c[1] as RequestInit)?.method === "PUT",
    );
    expect(putCall).toBeTruthy();
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsSecurity.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsSecurity.svelte`

- [ ] **Step 3: Create the component**

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsSecurity.svelte -->
<script lang="ts">
  import type { createAuthStore } from "../../authStore.svelte";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";
  import Modal from "../ui/Modal.svelte";

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

  .token-table { width: 100%; border-collapse: collapse; margin-top: var(--space-2); font-size: 0.875rem; }
  .token-table th { text-align: left; padding: 6px 8px; color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  .token-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); color: var(--text); }
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsSecurity.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsSecurity.svelte packages/editor/test/SettingsSecurity.test.ts
git commit -m "feat: extract SettingsSecurity panel (API Tokens, Users, SSO)"
```

---

### Task 6: Extract `SettingsIntegrations.svelte` (MCP Server)

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsIntegrations.svelte`
- Test: `packages/editor/test/SettingsIntegrations.test.ts`
- Reference (unchanged for now): `SettingsPage.svelte:432-461` (script), `:1416-1439` (markup)

Takes one prop: `authStore: AuthStore`.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsIntegrations.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsIntegrations from "../src/lib/components/settings/SettingsIntegrations.svelte";

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

describe("SettingsIntegrations", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/mcp/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: true, json: async () => ({ enabled: true }) });
      }
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("shows the MCP Server card for admin", async () => {
    const app = mount(SettingsIntegrations, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("MCP Server");
    unmount(app);
  });

  it("hides the MCP Server card for non-admin", () => {
    const app = mount(SettingsIntegrations, { target, props: { authStore: makeAuthStore("normal") } });
    flushSync();
    expect(target.querySelector(".ui-card")).toBeNull();
    unmount(app);
  });

  it("shows the connection URL once enabled", async () => {
    const app = mount(SettingsIntegrations, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Connection URL");
    const checkbox = target.querySelector('input[type="checkbox"]') as HTMLInputElement;
    checkbox.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Connection URL");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsIntegrations.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsIntegrations.svelte`

- [ ] **Step 3: Create the component**

```svelte
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsIntegrations.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsIntegrations.svelte packages/editor/test/SettingsIntegrations.test.ts
git commit -m "feat: extract SettingsIntegrations panel (MCP Server)"
```

---

### Task 7: Extract `SettingsBackup.svelte` (Backup & Restore + Scheduled Backups)

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsBackup.svelte`
- Test: `packages/editor/test/SettingsBackup.test.ts`
- Reference (unchanged for now): `SettingsPage.svelte:526-718` (script), `:1494-1602` (markup), `:1664-1674` (modal)

Takes **no props**.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsBackup.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsBackup from "../src/lib/components/settings/SettingsBackup.svelte";

function mockBoilerplateEndpoints(url: string): { ok: boolean; json: () => Promise<unknown> } | null {
  if (url === "/api/backup/config") {
    return {
      ok: true,
      json: async () => ({ enabled: false, frequency: "daily", time: "03:00", dayOfWeek: 7, dayOfMonth: 1, retentionCount: 7 }),
    };
  }
  if (url === "/api/backup/scheduled") return { ok: true, json: async () => [] };
  return null;
}

describe("SettingsBackup", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:fake");
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the Backup & Restore card with both buttons", () => {
    const app = mount(SettingsBackup, { target, props: {} });
    flushSync();
    expect(target.textContent).toContain("Backup & Restore");
    expect(target.textContent).toContain("Download Backup");
    expect(target.textContent).toContain("Restore from Backup");
    unmount(app);
  });

  it("calls GET /api/backup/download when Download Backup is clicked", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response("fake-zip-content", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="myhome-backup-2026-06-29.zip"' },
      }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsBackup, { target, props: {} });
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("Download Backup"))!;
    btn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchMock).toHaveBeenCalledWith("/api/backup/download");
    unmount(app);
  });

  it("shows confirmation modal and posts FormData on confirm", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response(null, { status: 204 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsBackup, { target, props: {} });
    flushSync();
    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    const restoreBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Restore")!;
    restoreBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchMock).toHaveBeenCalledWith("/api/backup/restore", expect.objectContaining({ method: "POST" }));
    unmount(app);
  });

  it("renders the Scheduled Backups section with defaults", async () => {
    const app = mount(SettingsBackup, { target, props: {} });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Scheduled Backups");
    expect((target.querySelector(".backup-enable-toggle") as HTMLInputElement).checked).toBe(false);
    unmount(app);
  });

  it("Run backup now calls POST /api/backup/scheduled/run", async () => {
    const app = mount(SettingsBackup, { target, props: {} });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const runBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Run backup now"))!;
    (runBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchMock).toHaveBeenCalledWith("/api/backup/scheduled/run", expect.objectContaining({ method: "POST" }));
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsBackup.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsBackup.svelte`

- [ ] **Step 3: Create the component**

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsBackup.svelte -->
<script lang="ts">
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";
  import Modal from "../ui/Modal.svelte";

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

  interface ScheduledBackupConfig {
    enabled: boolean;
    frequency: "daily" | "weekly" | "monthly";
    time: string;
    dayOfWeek: number;
    dayOfMonth: number;
    retentionCount: number;
  }
  interface ScheduledBackupEntry {
    filename: string;
    createdAt: string;
    sizeBytes: number;
  }

  function defaultBackupConfig(): ScheduledBackupConfig {
    return { enabled: false, frequency: "daily", time: "03:00", dayOfWeek: 7, dayOfMonth: 1, retentionCount: 7 };
  }

  const WEEKDAY_OPTIONS = [
    { value: 1, label: "Monday" }, { value: 2, label: "Tuesday" }, { value: 3, label: "Wednesday" },
    { value: 4, label: "Thursday" }, { value: 5, label: "Friday" }, { value: 6, label: "Saturday" },
    { value: 7, label: "Sunday" },
  ];

  let scheduledConfig = $state<ScheduledBackupConfig>(defaultBackupConfig());
  let scheduledConfigLoaded = $state(false);
  let scheduledConfigError = $state<string | null>(null);
  let scheduledConfigSaving = $state(false);
  let scheduledDayOfMonthStr = $state(String(defaultBackupConfig().dayOfMonth));
  let scheduledRetentionCountStr = $state(String(defaultBackupConfig().retentionCount));
  let scheduledBackups = $state<ScheduledBackupEntry[]>([]);
  let runningBackupNow = $state(false);
  let confirmDeleteBackupFilename = $state<string | null>(null);

  async function loadScheduledBackupConfig(): Promise<void> {
    const resp = await fetch("/api/backup/config");
    if (resp.ok) {
      scheduledConfig = await resp.json();
      scheduledDayOfMonthStr = String(scheduledConfig.dayOfMonth);
      scheduledRetentionCountStr = String(scheduledConfig.retentionCount);
    }
    scheduledConfigLoaded = true;
  }

  async function loadScheduledBackups(): Promise<void> {
    const resp = await fetch("/api/backup/scheduled");
    if (resp.ok) scheduledBackups = await resp.json();
  }

  loadScheduledBackupConfig();
  loadScheduledBackups();

  async function saveScheduledBackupConfig(): Promise<void> {
    scheduledConfigError = null;
    scheduledConfigSaving = true;
    try {
      const resp = await fetch("/api/backup/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...scheduledConfig,
          dayOfMonth: parseInt(scheduledDayOfMonthStr, 10) || 1,
          retentionCount: parseInt(scheduledRetentionCountStr, 10) || 1,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      scheduledConfig = await resp.json();
      scheduledDayOfMonthStr = String(scheduledConfig.dayOfMonth);
      scheduledRetentionCountStr = String(scheduledConfig.retentionCount);
    } catch (e) {
      scheduledConfigError = e instanceof Error ? e.message : String(e);
    } finally {
      scheduledConfigSaving = false;
    }
  }

  async function runBackupNow(): Promise<void> {
    runningBackupNow = true;
    scheduledConfigError = null;
    try {
      const resp = await fetch("/api/backup/scheduled/run", { method: "POST" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      await loadScheduledBackups();
    } catch (e) {
      scheduledConfigError = e instanceof Error ? e.message : String(e);
    } finally {
      runningBackupNow = false;
    }
  }

  function formatBackupSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function downloadScheduledBackup(filename: string): Promise<void> {
    const resp = await fetch(`/api/backup/scheduled/${filename}/download`);
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function deleteScheduledBackup(filename: string): Promise<void> {
    await fetch(`/api/backup/scheduled/${filename}`, { method: "DELETE" });
    confirmDeleteBackupFilename = null;
    await loadScheduledBackups();
  }
</script>

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

  <h3 class="subsection-title" style="margin-top: var(--space-4)">Scheduled Backups</h3>
  {#if scheduledConfigLoaded}
    <label class="module-row">
      <input class="backup-enable-toggle" type="checkbox" bind:checked={scheduledConfig.enabled} />
      <span class="mod-label">Enable scheduled backups</span>
    </label>
    {#if scheduledConfig.enabled}
      <div class="modal-form" style="margin-top: var(--space-3)">
        <div class="modal-field">
          <span class="modal-label">Frequency</span>
          <select bind:value={scheduledConfig.frequency} class="modal-select">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        {#if scheduledConfig.frequency === "weekly"}
          <div class="modal-field">
            <span class="modal-label">Day of week</span>
            <select bind:value={scheduledConfig.dayOfWeek} class="modal-select">
              {#each WEEKDAY_OPTIONS as opt (opt.value)}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </div>
        {/if}
        {#if scheduledConfig.frequency === "monthly"}
          <div class="modal-field">
            <span class="modal-label">Day of month</span>
            <Input type="number" bind:value={scheduledDayOfMonthStr} />
          </div>
        {/if}
        <div class="modal-field">
          <span class="modal-label">Time (UTC, HH:MM)</span>
          <Input bind:value={scheduledConfig.time} placeholder="03:00" />
        </div>
        <div class="modal-field">
          <span class="modal-label">Keep last N backups</span>
          <Input type="number" bind:value={scheduledRetentionCountStr} />
        </div>
      </div>
    {/if}
    {#if scheduledConfigError}<div class="error">{scheduledConfigError}</div>{/if}
    <div class="modal-actions">
      <Button onclick={saveScheduledBackupConfig} disabled={scheduledConfigSaving}>
        {scheduledConfigSaving ? "Saving…" : "Save"}
      </Button>
      <Button variant="secondary" onclick={runBackupNow} disabled={runningBackupNow}>
        {runningBackupNow ? "Running…" : "Run backup now"}
      </Button>
    </div>
  {/if}

  {#if scheduledBackups.length > 0}
    <div class="table-wrapper" style="margin-top: var(--space-3)">
      <table>
        <thead>
          <tr><th>Created</th><th>Size</th><th></th></tr>
        </thead>
        <tbody>
          {#each scheduledBackups as backup (backup.filename)}
            <tr class="backup-row">
              <td>{new Date(backup.createdAt).toLocaleString()}</td>
              <td>{formatBackupSize(backup.sizeBytes)}</td>
              <td class="actions">
                {#if confirmDeleteBackupFilename === backup.filename}
                  <span class="confirm-text">Delete?</span>
                  <button class="icon-action danger" onclick={() => deleteScheduledBackup(backup.filename)}>✓</button>
                  <button class="icon-action" onclick={() => { confirmDeleteBackupFilename = null; }}>✕</button>
                {:else}
                  <button class="icon-action" onclick={() => downloadScheduledBackup(backup.filename)} title="Download">⬇</button>
                  <button class="icon-action danger" onclick={() => { confirmDeleteBackupFilename = backup.filename; }} title="Delete">🗑</button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</Card>

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
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }
  .hidden-file-input { display: none; }

  .subsection-title { margin: 0 0 var(--space-2); font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: .05em; }

  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-label { font-size: 13px; color: var(--text); }

  .modal-form { display: flex; flex-direction: column; gap: 14px; }
  .modal-field { display: flex; flex-direction: column; gap: 5px; }
  .modal-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .modal-select { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; color: var(--text); font-size: 0.9rem; font-family: var(--font-sans); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }

  .table-wrapper { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  thead { background: var(--surface-alt); }
  th { padding: 5px 10px; color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: .05em; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface-hover); }

  .actions { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
  .icon-action { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; padding: 2px 5px; border-radius: 3px; }
  .icon-action:hover { background: var(--surface-hover); color: var(--text-muted); }
  .icon-action.danger { color: var(--danger); }
  .icon-action.danger:hover { background: color-mix(in srgb, var(--danger) 18%, var(--surface)); }
  .confirm-text { font-size: 10px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsBackup.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsBackup.svelte packages/editor/test/SettingsBackup.test.ts
git commit -m "feat: extract SettingsBackup panel (Backup & Restore + Scheduled Backups)"
```

---

### Task 8: Extract `SettingsActivityLog.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsActivityLog.svelte`
- Test: `packages/editor/test/SettingsActivityLog.test.ts`
- Reference (unchanged for now): `SettingsPage.svelte:722-779` (script), `:1604-1659` (markup)

Takes one prop: `authStore: AuthStore`.

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsActivityLog.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsActivityLog from "../src/lib/components/settings/SettingsActivityLog.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

describe("SettingsActivityLog", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    homesStore.setActiveHomeId("home-1");
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.startsWith("/api/homes/home-1/activity")) {
        return Promise.resolve({ ok: true, json: async () => ({ entries: [], total: 0 }) });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    homesStore._reset();
    target.remove();
  });

  it("renders the Activity Log section for admin", async () => {
    const app = mount(SettingsActivityLog, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Activity Log");
    unmount(app);
  });

  it("does not render for non-admin", async () => {
    const app = mount(SettingsActivityLog, { target, props: { authStore: makeAuthStore("normal") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Activity Log");
    unmount(app);
  });

  it("renders returned entries with description", async () => {
    fetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/api/homes/home-1/activity")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            entries: [{
              id: "e1", timestamp: "2026-07-08T12:00:00+00:00", userId: "u1", username: "alice",
              module: "works", action: "create", entityLabel: "Fix boiler", refId: null,
              description: "added work 'Fix boiler'",
            }],
            total: 1,
          }),
        });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    const app = mount(SettingsActivityLog, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("added work 'Fix boiler'");
    unmount(app);
  });

  it("applying a module filter re-fetches with the module query param", async () => {
    const app = mount(SettingsActivityLog, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const moduleSelect = target.querySelector(".activity-module-filter") as HTMLSelectElement;
    moduleSelect.value = "kb";
    moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(lastCall[0]).toContain("module=kb");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsActivityLog.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/settings/SettingsActivityLog.svelte`

- [ ] **Step 3: Create the component**

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsActivityLog.svelte -->
<script lang="ts">
  import type { createAuthStore } from "../../authStore.svelte";
  import Input from "../ui/Input.svelte";
  import Button from "../ui/Button.svelte";
  import Card from "../ui/Card.svelte";
  import { homesStore } from "../../homesStore.svelte";

  type AuthStore = ReturnType<typeof createAuthStore>;

  interface Props {
    authStore: AuthStore;
  }
  let { authStore }: Props = $props();

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
    if (authStore.user?.role !== "admin" || !homesStore.activeHomeId) { activityLoaded = true; return; }
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

{#if authStore.user?.role === "admin"}
  <Card>
    <div class="section-header">
      <h2>Activity Log</h2>
    </div>
    <div class="modal-form">
      <div class="modal-field">
        <span class="modal-label">Module</span>
        <select class="activity-module-filter modal-select" bind:value={activityModuleFilter} onchange={applyActivityFilters}>
          <option value="">All modules</option>
          <option value="chores">Chores</option>
          <option value="works">Works</option>
          <option value="costs">Costs</option>
          <option value="inventory">Inventory</option>
          <option value="consumables">Consumables</option>
          <option value="kb">Knowledge Base</option>
        </select>
      </div>
      <div class="modal-field">
        <span class="modal-label">From</span>
        <Input type="date" bind:value={activitySinceFilter} />
      </div>
      <div class="modal-field">
        <span class="modal-label">To</span>
        <Input type="date" bind:value={activityUntilFilter} />
      </div>
      <div class="modal-actions">
        <Button variant="secondary" onclick={applyActivityFilters}>Filter</Button>
      </div>
    </div>
    {#if activityLoaded}
      {#if activityEntries.length === 0}
        <p class="empty-hint">No activity recorded yet.</p>
      {:else}
        <table class="token-table">
          <thead>
            <tr><th>When</th><th>Who</th><th>What</th></tr>
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
          <Button variant="secondary" onclick={loadMoreActivity}>Load more</Button>
        {/if}
      {/if}
    {/if}
  </Card>
{/if}

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsActivityLog.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsActivityLog.svelte packages/editor/test/SettingsActivityLog.test.ts
git commit -m "feat: extract SettingsActivityLog panel"
```

---

### Task 9: Rewrite `SettingsPage.svelte` as the nav shell

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte` (full rewrite, replacing all 1839 lines)
- Modify: `packages/editor/test/SettingsPage.test.ts` (full rewrite, replacing all 906 lines)

All 7 panels and the nav exist and are independently tested (Tasks 1-8). This task performs the cutover: replace the monolith with the thin shell, and replace the old all-sections-on-one-page test suite with a slim wiring test (since section-specific behavior is now covered by each panel's own test file).

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/SettingsPage.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsPage from "../src/lib/components/SettingsPage.svelte";

function makeStore() {
  return {
    costCategories: [],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
    consumableUnits: [],
    consumableCategories: [],
    notificationSettings: {
      enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
      haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
    },
    loaded: true,
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
    updateNotificationSettings: vi.fn(),
  };
}

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

describe("SettingsPage — nav shell", () => {
  let target: HTMLDivElement;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("shows the General panel by default", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    expect(target.textContent).toContain("Home");
    expect(target.textContent).toContain("Modules");
    unmount(app);
  });

  it("shows all 7 groups for an admin, including Integrations and Activity Log", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("General"))).toBe(true);
    expect(labels.some((l) => l?.includes("Categories"))).toBe(true);
    expect(labels.some((l) => l?.includes("Notifications"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(true);
    expect(labels.some((l) => l?.includes("Backup & Restore"))).toBe(true);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    unmount(app);
  });

  it("hides Integrations and Activity Log for a non-admin, but keeps Security & Access", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal") } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(false);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(false);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    unmount(app);
  });

  it("switching to Categories via the nav shows the category sub-tabs", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    const categoriesBtn = [...target.querySelectorAll<HTMLButtonElement>(".nav-item")].find((b) => b.textContent?.includes("Categories"))!;
    categoriesBtn.click();
    flushSync();
    expect(target.textContent).toContain("Cost categories");
    expect(target.textContent).not.toContain("Home");
    unmount(app);
  });

  it("the mobile dropdown lists the same groups as the sidebar", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    const sidebarCount = target.querySelectorAll(".nav-item").length;
    const dropdownCount = target.querySelectorAll(".nav-select option").length;
    expect(dropdownCount).toBe(sidebarCount);
    unmount(app);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsPage.test.ts`
Expected: FAIL — old `SettingsPage.svelte` still renders every section on one page ("Home" is only the first text match, but "Cost categories" etc. are all present simultaneously so the "switching" and "hides Integrations" assertions fail).

- [ ] **Step 3: Rewrite `SettingsPage.svelte`**

```svelte
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
  }
  let { store, authStore }: Props = $props();

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
    { id: "activity", icon: "📜", label: "Activity Log", adminOnly: true },
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
        <SettingsIntegrations {authStore} />
      {:else if activeGroup === "backup"}
        <SettingsBackup />
      {:else if activeGroup === "activity"}
        <SettingsActivityLog {authStore} />
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/SettingsPage.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/test/SettingsPage.test.ts
git commit -m "refactor: rewrite SettingsPage as a sidebar-navigated shell over the extracted panels"
```

---

### Task 10: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd packages/editor && npm test`
Expected: All test files pass, including every new `Settings*.test.ts` file and the existing untouched suites (`settingsStore.test.ts`, `homesStore.test.ts`, `ConsumableModal.test.ts`, etc.).

- [ ] **Step 2: Run the TypeScript/Svelte type checker**

Run: `cd packages/editor && npm run typecheck`
Expected: No errors. Pay particular attention to any leftover import path mistakes in the new `settings/` files (e.g. `../ui/...` vs `../../ui/...`).

- [ ] **Step 3: Manual smoke check in the dev server**

Run: `cd packages/editor && npm run dev`, then open the app and navigate to Settings.

Verify:
- General shows by default (Home + Modules).
- Clicking each of the 7 sidebar entries swaps the content area without a page reload.
- As an admin: all 7 entries are visible, including Integrations and Activity Log.
- Log in (or simulate) as a non-admin: Integrations and Activity Log are absent from the sidebar; Security & Access is present and shows API Tokens but not Users/SSO.
- Resize the browser below ~720px width: the sidebar disappears and a dropdown selector appears at the top, and selecting an option switches panels.
- Within Categories, switching between the 5 sub-tabs (Cost/Inventory/Work/Suppliers/Consumables) shows one at a time.

- [ ] **Step 4: Commit if any fixes were needed during verification**

```bash
git add -A
git commit -m "fix: address issues found during settings reorganization verification"
```

(Skip this step if verification passed with no changes.)
