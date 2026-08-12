# KB & Chores UI Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four small KB/Chores UI issues: an unclear tree disclosure icon, a text-based save-status indicator, a missing edit-icon affordance, and rename "Room" to "Zone" throughout the app's display text.

**Architecture:** All four are display-layer-only changes in the Svelte 5 frontend (`packages/editor`). No backend, schema, or MCP changes. Task 1–3 touch `KBTree.svelte`/`KBPage.svelte` markup, CSS, and their component tests. Task 4 touches only `en.json`/`fr.json` string values (no key renames).

**Tech Stack:** Svelte 5, TypeScript, vitest + `svelte`'s `mount`/`unmount`/`flushSync` for component tests, svelte-i18n.

## Global Constraints

- Design doc: `docs/superpowers/specs/2026-08-12-kb-chores-ui-fixes-design.md` — display-text-only, no internal identifier renames (`roomId`, `Room` type, DB columns, MCP params all stay).
- Run `npm test` (vitest) from `packages/editor/` after each task; all tests must pass, including `test/i18nCompleteness.test.ts` which enforces en/fr key-set parity.
- Follow the existing pencil-icon edit-button convention already used elsewhere in the app (`title={$_('common.edit')}`, glyph `✏`) rather than inventing new copy — see `SettingsCategories.svelte`, `LocationsMatrix.svelte`.
- Test files live in `packages/editor/test/`, using `mount`/`unmount`/`flushSync` from `svelte` with `target` appended to `document.body` (jsdom event delegation requires this).

---

### Task 1: KB tree disclosure icon — rotating chevron + tooltip

**Files:**
- Modify: `packages/editor/src/lib/components/ui/KBTree.svelte:174-179` (markup), `:258-264` (`.disclosure` CSS)
- Test: `packages/editor/test/KBTree.test.ts`

**Interfaces:** No prop/interface changes — `ontoggle`, `collapsedIds`, `isOpen()` all unchanged.

- [ ] **Step 1: Write the failing test**

Add to the `describe("KBTree — selection", ...)` block in `packages/editor/test/KBTree.test.ts` (after the existing "clicking the disclosure triangle toggles without selecting" test):

```ts
  it("shows the disclosure button rotated open and with a title tooltip when expanded", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      collapsedIds: new Set(),
    });
    const disclosure = target.querySelector(".disclosure") as HTMLElement;
    expect(disclosure.className).toContain("open");
    expect(disclosure.getAttribute("title")).toBe("Collapse");
    expect(disclosure.textContent).toBe("▸");
    unmount(comp); target.remove();
  });

  it("shows the disclosure button not rotated and with a title tooltip when collapsed", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      collapsedIds: new Set(["p"]),
    });
    const disclosure = target.querySelector(".disclosure") as HTMLElement;
    expect(disclosure.className).not.toContain("open");
    expect(disclosure.getAttribute("title")).toBe("Expand");
    expect(disclosure.textContent).toBe("▸");
    unmount(comp); target.remove();
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/KBTree.test.ts`
Expected: FAIL — `disclosure.className` does not contain "open" (no such class exists yet), and `textContent` is `▼`/`▶` not `▸`.

- [ ] **Step 3: Update the component**

In `packages/editor/src/lib/components/ui/KBTree.svelte`, replace lines 174-179:

```svelte
        {#if hasChildren(entry.id)}
          <button
            class="disclosure"
            onclick={(e) => { e.stopPropagation(); ontoggle(entry.id); }}
            aria-label={isOpen(entry.id) ? $_('kb.tree.collapse') : $_('kb.tree.expand')}
          >{isOpen(entry.id) ? "▼" : "▶"}</button>
```

with:

```svelte
        {#if hasChildren(entry.id)}
          <button
            class="disclosure"
            class:open={isOpen(entry.id)}
            onclick={(e) => { e.stopPropagation(); ontoggle(entry.id); }}
            aria-label={isOpen(entry.id) ? $_('kb.tree.collapse') : $_('kb.tree.expand')}
            title={isOpen(entry.id) ? $_('kb.tree.collapse') : $_('kb.tree.expand')}
          >▸</button>
```

Then update the `.disclosure` CSS block (lines 258-264):

```css
  .disclosure {
    display: flex; align-items: center; justify-content: center;
    background: none; border: none; padding: 0; width: 18px; height: 18px; flex-shrink: 0;
    color: var(--text); font-size: 13px; line-height: 1; cursor: pointer; border-radius: var(--radius-sm);
    transition: transform 0.15s ease;
  }
  .disclosure.open { transform: rotate(90deg); }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/KBTree.test.ts`
Expected: PASS (all tests in the file, including the two new ones and the pre-existing "clicking the disclosure triangle toggles without selecting" test which only checks the `ontoggle` call, unaffected by the glyph/class change).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/KBTree.svelte packages/editor/test/KBTree.test.ts
git commit -m "fix(kb): rotate a single chevron for the tree disclosure toggle and add a hover tooltip"
```

---

### Task 2: KB save status → icon (spinner/check/warning)

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte:562-568` (markup), `:743-744` (`.save-status` CSS, add `@keyframes spin`)
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:** `saveStatus` state machine (`"idle" | "pending" | "saving" | "saved" | "error"`, declared at `KBPage.svelte:36`) is unchanged — this task only changes how each state renders.

- [ ] **Step 1: Write the failing test**

In `packages/editor/test/KBPage.test.ts`, inside `describe("KBPage — autosave", ...)`, replace the two tests that assert on visible "Saving"/"Saved" text:

Replace:
```ts
  it("saves automatically ~1.2s after the user stops typing, without a Save button", async () => {
    const { target, comp, store } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    expect(target.querySelector('[title="Save"]')).toBeNull();
    enterEditMode(target);
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(target.textContent).toContain("Saving");
    await new Promise((r) => setTimeout(r, 1300));
    flushSync();
    await tick(); flushSync();
    expect(store.entries.find((e) => e.id === "e1")?.content).toBe("hello world");
    unmount(comp); target.remove();
  });

  it("shows a Saved indicator after a successful autosave", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    enterEditMode(target);
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    await new Promise((r) => setTimeout(r, 1300));
    await tick(); flushSync();
    expect(target.textContent).toContain("Saved");
    unmount(comp); target.remove();
  });
```

with:
```ts
  it("saves automatically ~1.2s after the user stops typing, without a Save button, showing a spinning save-status icon", async () => {
    const { target, comp, store } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    expect(target.querySelector('[title="Save"]')).toBeNull();
    enterEditMode(target);
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const status = target.querySelector(".save-status") as HTMLElement;
    expect(status.getAttribute("title")).toBe("Saving…");
    expect(status.className).toContain("save-status-saving");
    await new Promise((r) => setTimeout(r, 1300));
    flushSync();
    await tick(); flushSync();
    expect(store.entries.find((e) => e.id === "e1")?.content).toBe("hello world");
    unmount(comp); target.remove();
  });

  it("shows a Saved indicator (checkmark icon with tooltip) after a successful autosave", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    enterEditMode(target);
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    await new Promise((r) => setTimeout(r, 1300));
    await tick(); flushSync();
    const status = target.querySelector(".save-status") as HTMLElement;
    expect(status.getAttribute("title")).toBe("Saved");
    expect(status.className).not.toContain("save-status-saving");
    unmount(comp); target.remove();
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts -t "autosave"`
Expected: FAIL — `.save-status` has no `title` attribute yet (only text content), and no `save-status-saving` class exists.

- [ ] **Step 3: Update the component**

In `packages/editor/src/lib/components/KBPage.svelte`, replace lines 562-568:

```svelte
            <span class="save-status" class:save-status-error={saveStatus === "error"}>
              {#if saveStatus === "saving" || saveStatus === "pending"}{$_('kb.page.saving')}
              {:else if saveStatus === "saved"}{$_('kb.page.saved')}
              {:else if saveStatus === "error"}{$_('kb.page.saveFailed')}
              {/if}
            </span>
```

with:

```svelte
            <span
              class="save-status"
              class:save-status-saving={saveStatus === "saving" || saveStatus === "pending"}
              class:save-status-error={saveStatus === "error"}
              title={saveStatus === "saving" || saveStatus === "pending" ? $_('kb.page.saving') : saveStatus === "saved" ? $_('kb.page.saved') : saveStatus === "error" ? $_('kb.page.saveFailed') : undefined}
            >
              {#if saveStatus === "saving" || saveStatus === "pending"}↻
              {:else if saveStatus === "saved"}✓
              {:else if saveStatus === "error"}⚠
              {/if}
            </span>
```

Then replace the `.save-status`/`.save-status-error` CSS (lines 743-744):

```css
  .save-status { font-size: 13px; color: var(--text-muted); white-space: nowrap; display: inline-flex; align-items: center; }
  .save-status-saving { display: inline-block; animation: kb-spin 0.8s linear infinite; }
  .save-status-error { color: var(--danger); }

  @keyframes kb-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (full file, not just the autosave subset, to catch any other test touching `.save-status`).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "fix(kb): show save status as a spinner/check/warning icon instead of text"
```

---

### Task 3: KB edit icon button

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte:561-572` (header-actions)
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:** Consumes the existing `editing` `$state<boolean>` (declared `KBPage.svelte:31`) and `contentTab` `$state` (declared `:30`) — sets `editing = true` directly, exactly what `MarkdownEditor`'s internal dblclick handler already does via its `$bindable()` `editing` prop (`MarkdownEditor.svelte:47,248`). No new state.

- [ ] **Step 1: Write the failing test**

In `packages/editor/test/KBPage.test.ts`, replace the existing test:

```ts
  it("double-click on the preview enters edit mode; there is no separate Edit button", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    expect(target.querySelector('[title="Edit"]')).toBeNull();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    enterEditMode(target);
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(comp); target.remove();
  });
```

with:

```ts
  it("double-click on the preview enters edit mode", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    enterEditMode(target);
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(comp); target.remove();
  });

  it("shows an Edit icon button that also enters edit mode, and hides itself once editing", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    const editBtn = target.querySelector('[title="Edit"]') as HTMLElement;
    expect(editBtn).not.toBeNull();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    editBtn.click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    expect(target.querySelector('[title="Edit"]')).toBeNull();
    unmount(comp); target.remove();
  });
```

(`enterEditMode` is the existing helper defined at the top of the `describe("KBPage — autosave", ...)` block — no change needed there.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts -t "Edit icon"`
Expected: FAIL — no element with `title="Edit"` exists yet.

- [ ] **Step 3: Update the component**

In `packages/editor/src/lib/components/KBPage.svelte`, replace the `header-actions` block (lines 561-572):

```svelte
        <div class="header-actions">
          {#if contentTab === "content" && editing}
            <span class="save-status" class:save-status-error={saveStatus === "error"}>
              {#if saveStatus === "saving" || saveStatus === "pending"}{$_('kb.page.saving')}
              {:else if saveStatus === "saved"}{$_('kb.page.saved')}
              {:else if saveStatus === "error"}{$_('kb.page.saveFailed')}
              {/if}
            </span>
            <Button variant="primary" onclick={handleDoneEditing} title={$_('works.modal.doneEditing')}>✓</Button>
          {/if}
          <Button variant="ghost" onclick={() => handleAskDelete(selectedEntry.id)} title={$_('kb.page.deletePage')}>🗑</Button>
        </div>
```

with (the `save-status` span here reflects Task 2's edit — apply both edits together, this is the combined result):

```svelte
        <div class="header-actions">
          {#if contentTab === "content" && editing}
            <span
              class="save-status"
              class:save-status-saving={saveStatus === "saving" || saveStatus === "pending"}
              class:save-status-error={saveStatus === "error"}
              title={saveStatus === "saving" || saveStatus === "pending" ? $_('kb.page.saving') : saveStatus === "saved" ? $_('kb.page.saved') : saveStatus === "error" ? $_('kb.page.saveFailed') : undefined}
            >
              {#if saveStatus === "saving" || saveStatus === "pending"}↻
              {:else if saveStatus === "saved"}✓
              {:else if saveStatus === "error"}⚠
              {/if}
            </span>
            <Button variant="primary" onclick={handleDoneEditing} title={$_('works.modal.doneEditing')}>✓</Button>
          {:else if contentTab === "content" && !editing}
            <Button variant="ghost" onclick={() => { editing = true; }} title={$_('common.edit')}>✏</Button>
          {/if}
          <Button variant="ghost" onclick={() => handleAskDelete(selectedEntry.id)} title={$_('kb.page.deletePage')}>🗑</Button>
        </div>
```

*(If Task 2 was implemented first, only add the new `{:else if contentTab === "content" && !editing}` branch and its `Button` — don't duplicate the save-status edit.)*

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): add an Edit icon button alongside double-click-to-edit"
```

---

### Task 4: Rename "Room" to "Zone" in display text (floor plan + Chores + Costs + Inventory)

**Files:**
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: none new (existing `test/i18nCompleteness.test.ts` covers key-set parity; no test currently asserts on any of these specific string values — verified by grep before writing this plan)

**Interfaces:** None — value-only edits, no key renamed, no component touched (all consuming components already read these keys via `$_()`).

- [ ] **Step 1: Edit `en.json`**

Change these 13 values (key path unchanged, only the string value). Line numbers are current-as-of-this-plan; re-locate by key path if the file has since shifted.

| Line | Key | Old value | New value |
|---|---|---|---|
| 257 | `floorPlan.roomPanel.title` | `"Room"` | `"Zone"` |
| 271 | `floorPlan.openingPanel.noArea` | `"Assign this room to an HA Area first"` | `"Assign this zone to an HA Area first"` |
| 434 | `chores.badgePopup.thisRoom` | `"This room"` | `"This zone"` |
| 439 | `chores.list.roomInFloor` | `"Room ({floor})"` | `"Zone ({floor})"` |
| 440 | `chores.list.unknownRoom` | `"Unknown room"` | `"Unknown zone"` |
| 445 | `chores.list.emptyState` | `"No chore assignments yet. Go to Management to create chores and assign them to rooms."` | `"No chore assignments yet. Go to Management to create chores and assign them to zones."` |
| 475 | `chores.editModal.selectRoom` | `"Select a room…"` | `"Select a zone…"` |
| 486 | `chores.page.allRooms` | `"All rooms"` | `"All zones"` |
| 495 | `chores.page.notAssigned` | `"Not assigned to any room"` | `"Not assigned to any zone"` |
| 497 | `chores.page.rooms` | `"Rooms"` | `"Zones"` |
| 499 | `chores.page.roomCount` | `"{n} rooms"` | `"{n} zones"` |
| 885 | `costs.page.room` | `"Room"` | `"Zone"` |
| 901 | `costs.entryModal.noRoom` | `"No room"` | `"No zone"` |

(`floorPlan.roomPanel.haArea` is already `"HA Area"` in English — no change needed there.)

- [ ] **Step 2: Edit `fr.json`**

Same 13 key paths (line numbers currently identical to `en.json` since both files are kept in parallel structure), plus the naming-collision fix for `haArea`:

| Line | Key | Old value | New value |
|---|---|---|---|
| 257 | `floorPlan.roomPanel.title` | `"Pièce"` | `"Zone"` |
| 259 | `floorPlan.roomPanel.haArea` | `"Zone HA"` | `"HA Area"` |
| 271 | `floorPlan.openingPanel.noArea` | `"Associez d'abord cette pièce à une zone HA"` | `"Associez d'abord cette zone à une HA Area"` |
| 434 | `chores.badgePopup.thisRoom` | `"Cette pièce"` | `"Cette zone"` |
| 439 | `chores.list.roomInFloor` | `"Pièce ({floor})"` | `"Zone ({floor})"` |
| 440 | `chores.list.unknownRoom` | `"Pièce inconnue"` | `"Zone inconnue"` |
| 445 | `chores.list.emptyState` | `"Aucune corvée assignée pour l'instant. Rendez-vous dans Gestion pour créer des corvées et les assigner à des pièces."` | `"Aucune corvée assignée pour l'instant. Rendez-vous dans Gestion pour créer des corvées et les assigner à des zones."` |
| 475 | `chores.editModal.selectRoom` | `"Choisir une pièce…"` | `"Choisir une zone…"` |
| 486 | `chores.page.allRooms` | `"Toutes les pièces"` | `"Toutes les zones"` |
| 495 | `chores.page.notAssigned` | `"Non assignée à une pièce"` | `"Non assignée à une zone"` |
| 497 | `chores.page.rooms` | `"Pièces"` | `"Zones"` |
| 499 | `chores.page.roomCount` | `"{n} pièces"` | `"{n} zones"` |
| 885 | `costs.page.room` | `"Pièce"` | `"Zone"` |
| 901 | `costs.entryModal.noRoom` | `"Aucune pièce"` | `"Aucune zone"` |

Note: `floorPlan.roomPanel.label` (`"Nom"`) and the furniture-library category labels (`"Bathroom"`/`"Salle de bain"`, `"Bedroom"`, `"Living Room"`, `"Garden"`) are explicitly out of scope per the design doc — do not touch them.

- [ ] **Step 3: Run the full frontend test suite**

Run: `cd packages/editor && npm test`
Expected: PASS, including `test/i18nCompleteness.test.ts` (key sets are unchanged, only values) and every other suite (grep confirmed beforehand that no test asserts on any of these 13 string values).

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "fix(chores,costs,inventory,floorplan): rename \"Room\" to \"Zone\" in display text"
```

---

## Final verification

- [ ] **Run the complete frontend suite once more from a clean state**

Run: `cd packages/editor && npm test`
Expected: PASS, all suites (this repo currently sits at 900+ frontend tests; expect that ballpark plus the ~4 new/modified ones from Tasks 1–3).

- [ ] **Manual smoke check** (per project convention of checking UI changes in a real browser before calling done): open the app, go to a KB page with sub-pages and confirm the disclosure chevron rotates on click with a hover tooltip; confirm the save-status icon spins while typing and shows a checkmark after ~1.2s; confirm the new pencil Edit button opens edit mode and disappears while editing, and double-click still also works; go to Chores/Costs/Inventory and the floor plan Room panel and confirm all "Room" text now reads "Zone" in both English and French.
