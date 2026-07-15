# Move Donetick Import to Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relocate the "Import from Donetick" button/token-input from the Chores page toolbar into a new admin-only Donetick card in Settings → Integrations, with no backend or behavior change.

**Architecture:** Pure frontend UI move. `App.svelte` passes `choreStore.importFromDonetick` down through `SettingsPage.svelte` to `SettingsIntegrations.svelte` as a narrow function prop; `SettingsIntegrations.svelte` gets a new admin-gated `Card` (mirroring the existing MCP Server card) that owns its own local import state. `ChoresPage.svelte` loses the equivalent toolbar block and state entirely.

**Tech Stack:** Svelte 5 (runes: `$state`, `$props`), Vitest + `svelte` mount/unmount for component tests.

## Global Constraints

- No backend changes: `POST /api/homes/{home_id}/chores/import` and `choreStore.importFromDonetick(token: string): Promise<number>` (in `packages/editor/src/lib/choreStore.svelte.ts:186`) are unchanged.
- Token is never persisted — entered fresh on every import, matching current behavior.
- New Donetick card is gated identically to the existing MCP Server card: `{#if authStore.user?.role === "admin"}`.
- Follow existing code style in each file (no new UI kit components beyond `Card`/`Button`/`Input`, already used in both files).

---

### Task 1: Add Donetick card to SettingsIntegrations.svelte

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsIntegrations.svelte`
- Test: `packages/editor/test/SettingsIntegrations.test.ts`

**Interfaces:**
- Consumes: none new (existing `authStore` prop). Adds new required prop `importFromDonetick: (token: string) => Promise<number>`.
- Produces: `SettingsIntegrations` now requires `importFromDonetick` — Task 2 (`SettingsPage.svelte`) must supply it.

- [ ] **Step 1: Write the failing tests**

Append to `packages/editor/test/SettingsIntegrations.test.ts`, inside the existing `describe("SettingsIntegrations", ...)` block (after the last `it(...)`, before the closing `});`):

```ts
  function makeImportFromDonetick(impl: (token: string) => Promise<number>) {
    return vi.fn(impl);
  }

  it("shows the Donetick card for admin", () => {
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick: makeImportFromDonetick(async () => 0) },
    });
    flushSync();
    expect(target.textContent).toContain("Donetick");
    unmount(app);
  });

  it("hides the Donetick card for non-admin", () => {
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("normal"), importFromDonetick: makeImportFromDonetick(async () => 0) },
    });
    flushSync();
    expect(target.textContent).not.toContain("Donetick");
    unmount(app);
  });

  it("imports from Donetick and shows the count", async () => {
    const importFromDonetick = makeImportFromDonetick(async (token) => {
      expect(token).toBe("secret-token");
      return 3;
    });
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const tokenInput = target.querySelector('input[placeholder="API token"]') as HTMLInputElement;
    tokenInput.value = "secret-token";
    tokenInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(importFromDonetick).toHaveBeenCalledWith("secret-token");
    expect(target.textContent).toContain("3 imported");
    unmount(app);
  });

  it("shows an error message when the import fails", async () => {
    const importFromDonetick = makeImportFromDonetick(async () => { throw new Error("boom"); });
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const tokenInput = target.querySelector('input[placeholder="API token"]') as HTMLInputElement;
    tokenInput.value = "bad-token";
    tokenInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Failed");
    unmount(app);
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/SettingsIntegrations.test.ts`
Expected: FAIL — `importFromDonetick` prop missing / "Donetick" text not found (component doesn't render the card yet).

- [ ] **Step 3: Implement the Donetick card**

In `packages/editor/src/lib/components/settings/SettingsIntegrations.svelte`, update the `<script>` block: add the new prop and local state (mirroring the removed `ChoresPage.svelte` state), keeping the existing `mcpEnabled`/`mcpConfigLoaded`/`mcpError`/`loadMcpConfig`/`toggleMcpEnabled` code untouched:

```svelte
<script lang="ts">
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
```

Add the new card in the markup, right after the closing `</Card>` of the MCP Server card and before the `{/if}`... actually the MCP card is itself wrapped in the admin `{#if}`, so add a second `<Card>` inside the same `{#if authStore.user?.role === "admin"}` block:

```svelte
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

  <Card>
    <div class="section-header">
      <h2>Donetick</h2>
    </div>
    <p class="section-desc">
      Imports chores from your Donetick instance into this home. Paste an API
      token from Donetick and click Import.
    </p>
    <div class="import-row">
      <Input type="password" placeholder="API token" bind:value={importToken} />
      <Button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? "Importing…" : "Import"}
      </Button>
      {#if importStatus === "error"}<span class="msg-error">Failed</span>{/if}
      {#if importStatus === "done"}<span class="msg-success">{importCount} imported</span>{/if}
    </div>
  </Card>
{/if}
```

Add to the `<style>` block (after the existing `.error` rule):

```css
  .import-row { display: flex; align-items: center; gap: 10px; margin-top: var(--space-2); }
  .msg-error { color: var(--danger); font-size: 11px; }
  .msg-success { color: var(--success); font-size: 11px; }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsIntegrations.test.ts`
Expected: PASS (all cases including the 3 pre-existing MCP ones).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsIntegrations.svelte packages/editor/test/SettingsIntegrations.test.ts
git commit -m "feat: add Donetick import card to Settings > Integrations"
```

---

### Task 2: Wire importFromDonetick through SettingsPage and App

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Modify: `packages/editor/src/App.svelte`

**Interfaces:**
- Consumes: `SettingsIntegrations` prop `importFromDonetick: (token: string) => Promise<number>` (from Task 1); `choreStore.importFromDonetick` (existing, `packages/editor/src/lib/choreStore.svelte.ts:186`).
- Produces: `SettingsPage` now requires a new prop `importFromDonetick: (token: string) => Promise<number>`.

- [ ] **Step 1: Update SettingsPage.svelte props and forward to SettingsIntegrations**

In `packages/editor/src/lib/components/SettingsPage.svelte`, update the `Props` interface and destructure:

```ts
  interface Props {
    store: SettingsStore;
    authStore: AuthStore;
    importFromDonetick: (token: string) => Promise<number>;
  }
  let { store, authStore, importFromDonetick }: Props = $props();
```

Find the existing render branch for the integrations group (search for `SettingsIntegrations` in the `{#if activeGroup === ...}` chain) and add the new prop to it:

```svelte
      {:else if activeGroup === "integrations"}
        <SettingsIntegrations {authStore} {importFromDonetick} />
```

(Keep whatever surrounding branch structure already exists — only add the `{importFromDonetick}` prop to the existing `<SettingsIntegrations>` usage.)

- [ ] **Step 2: Pass choreStore.importFromDonetick from App.svelte**

In `packages/editor/src/App.svelte`, find the existing `<SettingsPage store={settingsStore} {authStore} />` (around line 1273) and change it to:

```svelte
        <SettingsPage store={settingsStore} {authStore} importFromDonetick={choreStore.importFromDonetick} />
```

- [ ] **Step 3: Run the full frontend test suite to verify nothing broke**

Run: `cd packages/editor && npx vitest run`
Expected: PASS (no test currently mounts `SettingsPage` directly without the new prop — confirm by checking for a `SettingsPage.test.ts`; if one exists and fails to compile/type-check due to the new required prop, add `importFromDonetick: vi.fn(async () => 0)` to its mount props).

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/src/App.svelte
git commit -m "feat: wire Donetick import through Settings page to Chores store"
```

---

### Task 3: Remove Donetick import UI from ChoresPage.svelte

**Files:**
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte`
- Test: `packages/editor/test/ChoresPage.test.ts`

**Interfaces:**
- Consumes: none (pure removal).
- Produces: `ChoresPage.svelte` toolbar no longer contains Donetick import controls; `store.importFromDonetick` is no longer called from this file.

- [ ] **Step 1: Confirm there is no existing test asserting on the Donetick controls**

Run: `grep -n "Donetick\|Import from\|showImportInput" packages/editor/test/ChoresPage.test.ts`
Expected: no output (already verified during brainstorming — no existing test references this UI, so no test needs to be deleted). If this now shows output, remove the matching `it(...)` block before continuing.

- [ ] **Step 2: Remove the import state and handler**

In `packages/editor/src/lib/components/ChoresPage.svelte`, delete these lines (currently lines 54-57):

```ts
  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);
```

and delete `handleImport` (currently lines 178-184):

```ts
  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await store.importFromDonetick(importToken.trim());
      importStatus = "done"; importToken = ""; showImportInput = false;
    } catch { importStatus = "error"; }
  }
```

- [ ] **Step 3: Remove the toolbar markup block**

Delete this block from the toolbar (currently lines 262-272, immediately after the `<Button onclick={() => onnewchore?.()}>＋ Add chore</Button>` line):

```svelte
      {#if !showImportInput}
        <Button variant="secondary" onclick={() => { showImportInput = true; }}>Import from Donetick</Button>
      {:else}
        <Input type="password" placeholder="API token" bind:value={importToken} />
        <Button disabled={importStatus === "loading"} onclick={handleImport}>
          {importStatus === "loading" ? "Importing…" : "Import"}
        </Button>
        <Button variant="ghost" onclick={() => { showImportInput = false; }}>Cancel</Button>
        {#if importStatus === "error"}<span class="msg-error">Failed</span>{/if}
        {#if importStatus === "done"}<span class="msg-success">{importCount} imported</span>{/if}
      {/if}
```

- [ ] **Step 4: Remove the now-unused styles**

Run: `grep -n "msg-error\|msg-success" packages/editor/src/lib/components/ChoresPage.svelte`
Expected: only the two `<style>` rule lines remain (`.msg-error { ... }` and `.msg-success { ... }`). Delete both lines.

- [ ] **Step 5: Run the ChoresPage tests and full suite**

Run: `cd packages/editor && npx vitest run test/ChoresPage.test.ts`
Expected: PASS.

Run: `cd packages/editor && npx vitest run`
Expected: PASS (full suite green).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ChoresPage.svelte
git commit -m "refactor: remove Donetick import UI from Chores page toolbar"
```

---

## Final Verification

- [ ] Run `cd packages/editor && npx vitest run` once more — full suite green.
- [ ] Run `cd packages/editor && npx svelte-check` (or the project's equivalent type-check command) if available, to confirm no leftover type errors from the prop threading.
- [ ] Manually confirm (via `superpowers:verify` or the `run` skill) that: Chores page toolbar no longer shows "Import from Donetick"; Settings → Integrations shows a "Donetick" card for an admin user with a working Import flow.
