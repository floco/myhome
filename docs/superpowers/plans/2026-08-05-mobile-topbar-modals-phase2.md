# Mobile Responsiveness Phase 2: Topbar + Modals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the topbar from overflowing on narrow screens by hiding redundant text labels below 480px, and make modals fill the viewport edge-to-edge below 480px instead of rendering as a small centered floating box.

**Architecture:** All three changes are pure CSS additions (`@media (max-width: 480px)` blocks) — no new component state, no conditional rendering logic, no new props. The DOM structure is unchanged; only visibility/position/sizing changes at the breakpoint. This is spec Phase 2 of `docs/superpowers/specs/2026-08-05-mobile-responsive-audit-design.md`.

**Tech Stack:** Svelte 5, vitest (jsdom). **Important constraint discovered during planning: jsdom does not evaluate `@media` queries or compute cascaded CSS from `<style>` blocks** — `getComputedStyle` in this test environment only reflects inline styles, not stylesheet rules gated by a media query. This means the actual "hidden below 480px" / "full-screen below 480px" behavior cannot be asserted in a vitest unit test; it can only be verified in a real browser (Playwright, via the `webapp-testing` skill), matching how Phase 1's Task 13 verified `SortableTable`'s `hideBelow` CSS. Each task below is therefore CSS-only (grep-verified + full-suite-regression-checked, no red/green TDD cycle — there is no new testable logic), with a final Playwright task covering all three changes together in a real browser.

## Global Constraints

- Every new `@media` block uses the literal value `480px` (matching the `--bp-mobile` token added in Phase 1's `theme.css`, `packages/editor/src/lib/theme.css:53`) with a `/* --bp-mobile */` comment, per this project's documented breakpoint convention.
- Don't change any existing class names, DOM structure, or props — every change here is additive CSS inside each component's existing `<style>` block.
- Existing tests that assert on `.app-title`, `.topbar-current`, or `Modal`'s rendered structure must keep passing unmodified — these assertions don't depend on screen width and this phase doesn't change DOM structure, so they're expected to be unaffected by construction; the plan still runs the full suite after each task to confirm.

---

### Task 1: Hide the topbar page title below 480px

**Files:**
- Modify: `packages/editor/src/App.svelte:1349-1356` (`.topbar` rule) and `:1366-1369` (`.app-title` rule)

**Interfaces:**
- None — CSS-only change, no new props or state. `<span class="app-title">My Home</span>` (`App.svelte:785`) stays in the DOM unconditionally; only its CSS visibility changes.

- [ ] **Step 1: Add the media query**

In `packages/editor/src/App.svelte`, after the `.app-title { ... }` rule (lines 1366-1369), add:

```css
  @media (max-width: 480px) { /* --bp-mobile */
    .app-title { display: none; }
  }
```

- [ ] **Step 2: Verify**

Run: `grep -n "app-title { display: none" packages/editor/src/App.svelte`
Expected: one match, inside a `@media (max-width: 480px)` block.

- [ ] **Step 3: Run the full frontend test suite to confirm no regression**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS, same test/pass counts as before this change — `App.test.ts:107`'s `expect(target.querySelector(".app-title")?.textContent).toBe("My Home")` still passes because jsdom doesn't apply the media query (the element and its text content are unaffected; only real-browser CSS visibility changes).

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat(topbar): hide page title below 480px to free up space"
```

---

### Task 2: Hide the HomesSwitcher home-name label below 480px

**Files:**
- Modify: `packages/editor/src/lib/components/HomesSwitcher.svelte:170-183` (topbar-variant CSS)

**Interfaces:**
- None — CSS-only change. `<span class="topbar-name">{homesStore.activeHome?.name ?? "—"}</span>` (`HomesSwitcher.svelte:52`) stays in the DOM unconditionally; only its CSS visibility changes. `.topbar-icon` (⌂) and `.topbar-chevron` (▲/▼) stay visible at every width — only the home-name text hides, keeping the switcher tappable and recognizable as a control.

- [ ] **Step 1: Add the media query**

In `packages/editor/src/lib/components/HomesSwitcher.svelte`, after the `.topbar-chevron { ... }` rule (line 183), add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .topbar-name { display: none; }
  }
```

- [ ] **Step 2: Verify**

Run: `grep -n "topbar-name { display: none" packages/editor/src/lib/components/HomesSwitcher.svelte`
Expected: one match, inside a `@media (max-width: 480px)` block.

- [ ] **Step 3: Run the full frontend test suite to confirm no regression**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS — no existing test in `HomesSwitcher.test.ts` or `NavMenu.test.ts` asserts on `.topbar-name`'s visibility or text content, so none are affected.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/HomesSwitcher.svelte
git commit -m "feat(topbar): hide home name label in HomesSwitcher below 480px"
```

---

### Task 3: Make `Modal` full-screen below 480px

**Files:**
- Modify: `packages/editor/src/lib/components/ui/Modal.svelte:61-70` (`.ui-modal` rule)

**Interfaces:**
- None — CSS-only change. `width`, `title`, `open`, `onclose`, `children`, `footer` props are all unchanged. The inline `style="width: {width}"` (`Modal.svelte:39`) still renders on every modal; the new media query must win over it with `!important`, since inline styles otherwise take precedence over stylesheet rules regardless of specificity.

- [ ] **Step 1: Add the media query**

In `packages/editor/src/lib/components/ui/Modal.svelte`, after the `.ui-modal:focus { outline: none; }` rule (line 71), add:

```css

  @media (max-width: 480px) { /* --bp-mobile */
    .ui-modal {
      top: 0;
      left: 0;
      transform: none;
      width: 100% !important;
      height: 100%;
      max-width: 100vw;
      max-height: 100vh;
      border-radius: 0;
    }
  }
```

- [ ] **Step 2: Verify**

Run: `grep -n "width: 100% !important" packages/editor/src/lib/components/ui/Modal.svelte`
Expected: one match, inside a `@media (max-width: 480px)` block.

- [ ] **Step 3: Run the full frontend test suite to confirm no regression**

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS — `Modal.test.ts:61,76` assert `dialog.style.width` (the inline style attribute value, e.g. `"480px"`/`"560px"`), which is unaffected by adding a media-query CSS rule; jsdom doesn't apply it, and even in a real browser `element.style.width` (the inline attribute) still reads back as the original value — only the *rendered/computed* width changes at that breakpoint, which these tests don't assert.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/ui/Modal.svelte
git commit -m "feat(modal): fill the viewport edge-to-edge below 480px"
```

---

### Task 4: Real-browser verification across topbar + Modal

**Files:**
- None modified — verification-only, using the `webapp-testing` skill (Playwright), following the same isolated-instance recipe used for Phase 1's Task 13 (a stray main-repo dev server already runs on 8000/5173 with an unknown admin password — don't touch it; spin up a fresh isolated backend+frontend pair instead).

**Interfaces:**
- Consumes: the CSS from Tasks 1-3.

- [ ] **Step 1: Start an isolated instance**

```bash
mkdir -p /tmp/myhome-verify-phase2
cd packages/backend
PYTHONPATH=<worktree>/packages/backend/src DATA_DIR=/tmp/myhome-verify-phase2 uvicorn myhome.main:app --port 8011 --host 127.0.0.1 &
```

Read the generated admin password from `/tmp/myhome-verify-phase2/.initial-admin-password` once the log shows "First boot — admin password written to...".

Temporarily edit `packages/editor/vite.config.ts`'s `server.proxy["/api"]` to `http://localhost:8011`, then:

```bash
cd packages/editor
npm run dev -- --port 5182 --host 127.0.0.1 &
```

(If 5182 is taken, Vite will print the port it actually bound — use that one.)

- [ ] **Step 2: Log in, create a demo home, and check the topbar at 375px**

Using Playwright (via the `webapp-testing` skill): log in as `admin` with the password from Step 1, create a "Demo home" (pre-filled with sample data across every module) if prompted, then:

1. Set viewport to 375×667, `hasTouch: true`.
2. Navigate to any module route (e.g. `#/chores`).
3. Assert `.app-title` has `display: none` via `getComputedStyle` (this is the first point in this phase where that assertion is actually meaningful, since it's a real browser, not jsdom).
4. Assert `.topbar-name` (inside `HomesSwitcher`) has `display: none`.
5. Assert the topbar's rightmost element (`.user-chip`) has its bounding-box right edge `<= 375` (i.e., the topbar itself no longer overflows now that both labels are hidden — this was the ~487px document-overflow observed during Phase 1's Task 13 verification, which is fixed by this phase).
6. Take a screenshot for the record.

- [ ] **Step 3: Check Modal full-screen behavior at 375px**

Still at 375×667 viewport:

1. Open a small modal (e.g. click "+ Add chore" on the Chores page) and assert `.ui-modal`'s bounding box is `{top: 0, left: 0, width: 375, height: 667}` (or within a few px, accounting for scrollbar/viewport rounding) via `getBoundingClientRect()`.
2. Open one of the larger `min(92vw, 820px)`-width modals (e.g. the Insurance or Property edit modal) and confirm the same full-screen behavior applies (the media query overrides the inline width regardless of the modal's configured width prop).
3. Take a screenshot of both for the record.

- [ ] **Step 4: Fix any real issues found, following the same pattern as Phase 1's Task 13**

If the topbar still overflows or a modal doesn't go full-screen, diagnose with the systematic-debugging skill (Phase 1 uncovered a real flexbox `min-width`/`flex:none` interaction this way — check for a similar unexpected CSS interaction before assuming the media query itself is wrong) and commit the fix following the same commit-per-fix pattern as Tasks 1-3.

- [ ] **Step 5: Clean up the isolated instance**

```bash
git checkout -- packages/editor/vite.config.ts
```

Kill only the specific backend/frontend PIDs started in Step 1 (not any pre-existing dev server on 8000/5173), and remove `/tmp/myhome-verify-phase2`.
