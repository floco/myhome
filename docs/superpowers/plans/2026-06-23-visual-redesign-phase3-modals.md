# Visual Redesign Phase 3: Modals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the 6 Phase-3 target files (`NewChoreModal.svelte`, `InventoryModal.svelte`, `CostsEntryModal.svelte`, `CostsCategoryModal.svelte`, `WorkModal.svelte`, `DatePicker.svelte`) from hand-rolled, hardcoded-dark-color markup onto the shared `theme.css` tokens and the Phase-1 `Modal`/`Input`/`Button`/`StatTile` components, per the Spec 6 design doc's Phase 3 scope.

**Architecture:**
- The 5 dialog-style files (everything except `DatePicker.svelte`) wrap their hand-rolled `.overlay`/`.modal`/`.modal-header`/`.modal-footer` markup in the shared `<Modal>` component (`open`/`title`/`onclose`/children/`footer` snippet API), eliminating duplicated backdrop, header, and close-button code. Tabbed modals (`InventoryModal`, `WorkModal`) keep their existing hand-rolled tab-strip markup as plain content inside `<Modal>`'s default body — `Modal` itself gains no tabs concept.
- A form field is migrated to `<Input>` only when it is a plain single-line text field needing nothing beyond `value`/`placeholder` (no `maxlength`, `autofocus`, `list`, `type="number"`, etc.). Everything else (selects, textareas, checkboxes, file inputs, number/date inputs, datalist-bound inputs) stays a native element but is restyled to be visually identical to `<Input>` via a shared `.native-input` CSS recipe (same background/border/radius/padding/font as `ui-input`). This keeps the shared component's API narrow and avoids forcing every field through a one-size-fits-all wrapper.
- Every footer/action button that fits `<Button>`'s API (`variant`/`onclick`/`disabled`/`title`/children, no other attributes needed) migrates to `<Button>`. Small icon-only affordances (the attachment-row "✕" delete, the file-upload `<label>` trigger, the tab-strip buttons) stay native and token-styled, mirroring how `Modal.svelte` itself keeps its own header close button native rather than nesting a `<Button>`.
- `Button.svelte` gains a 4th variant, `"danger"` (solid `var(--danger)` background), since every dialog file has at least one destructive delete/confirm-delete button that doesn't fit `primary`/`secondary`/`ghost`. Both the outline "Delete" button and the solid "Confirm delete" button collapse onto this single `danger` variant — a deliberate simplification (previously two visually distinct red treatments, now one consistent one), matching the redesign's established "fewer, more consistent treatments" pattern from Phase 2.
- `Modal.svelte` gains an optional `width` prop (default `"480px"`, applied as an inline style so it always wins) since the target files need 360–820px modals, and `width: 480px` is removed from its own `.ui-modal` rule in favor of the inline override. `Modal.svelte`'s footer also gains `flex-wrap: wrap` so multi-button footers (delete-flow + save) wrap gracefully on narrow viewports — purely additive, doesn't change any single-button footer's layout.
- `WorkModal.svelte`'s three responsive width breakpoints (`min(95vw,560px)` → `min(90vw,760px)` → `min(80vw,960px)`) collapse into a single `width="min(92vw, 820px)"` value passed to `<Modal>`. This is an intentional simplification (one CSS value instead of three media-query tiers) consistent with the rest of this migration; it loses the very-wide-screen jump to 960px but keeps sensible sizing at all other widths.
- `DatePicker.svelte` is **not** wrapped in `<Modal>` (it's a popover widget, not a dialog) and its calendar grid does not become `<Input>`/`<Button>` instances (its trigger field and nav arrows are visually unlike a generic text input or button). It gets a pure token-color migration only, the same treatment Phase 2 gave `LayersDropdown.svelte`.
- `CostsCategoryModal.svelte`'s three stat chips switch to the existing `<StatTile value label>` component (Phase 1), with a `:global()` CSS override in the modal's own `<style>` block to match the original chips' more compact sizing.

**Tech Stack:** Svelte 5 (runes, snippets), Vitest, the existing `packages/editor/src/lib/theme.css` token set, `packages/editor/src/lib/components/ui/{Modal,Input,Button,StatTile}.svelte`.

---

## Task 1: Add `width` to Modal and `danger` variant to Button

**Files:**
- Modify: `packages/editor/src/lib/components/ui/Modal.svelte`
- Modify: `packages/editor/src/lib/components/ui/Button.svelte`
- Modify: `packages/editor/test/Modal.test.ts`
- Modify: `packages/editor/test/Button.test.ts`

**Status: DONE (commit 0c83fe8)**

---

## Task 2: Token-migrate DatePicker

**Files:**
- Modify: `packages/editor/src/lib/components/DatePicker.svelte`

**Status: DONE (commit af5bac3)**

---

## Task 3: Migrate NewChoreModal onto Modal/Button

**Files:**
- Modify: `packages/editor/src/lib/components/NewChoreModal.svelte`

**Status: DONE (commit 8008bc5)**

---

## Task 4: Migrate InventoryModal onto Modal/Input/Button/StatTile patterns

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryModal.svelte`

**Status: DONE (commit cb2227e)**

---

## Task 5: Migrate CostsEntryModal onto Modal/Button

**Files:**
- Modify: `packages/editor/src/lib/components/CostsEntryModal.svelte`

**Status: DONE (commit a85907a)**

---

## Task 6: Migrate CostsCategoryModal onto Modal/Button/StatTile

**Files:**
- Modify: `packages/editor/src/lib/components/CostsCategoryModal.svelte`

**Status: DONE (commit 1655c10)**

---

## Task 7: Migrate WorkModal onto Modal/Input/Button

**Files:**
- Modify: `packages/editor/src/lib/components/WorkModal.svelte`

**Status: DONE (commit 22a36b0)**

---

## Final Step: Holistic Review

After all 7 tasks are committed, dispatch a final code-reviewer subagent across the full `main..HEAD` diff to verify:
- No remaining hardcoded hex/rgba colors in any of the 7 touched files (`grep -rn '#[0-9a-fA-F]\{3,8\}\b\|rgba\?(' <files>` should only match SVG/chart `category.color` fallbacks that are now `var(--accent)`, not literal hex).
- Every footer button uses `<Button>` except the documented native exceptions (file-upload label, attachment-row delete ✕, tab-strip buttons).
- `danger` variant is used consistently for every delete/confirm-delete button across all 5 dialog files.
- `Modal`'s `width` prop is passed explicitly wherever a file needs something other than 480px.
- Final `npm test -- --run` passes with no regressions versus the pre-Phase-3 baseline count.

Note: the per-task "Step 1: Replace the entire file" code blocks that were originally in this document (full literal file contents for each task) were the ones actually executed and are now reflected verbatim in the corresponding git commits listed above — see `git show <commit>` for the exact content of each migration. This document was regenerated after the original on-disk copy was lost to an untracked-file cleanup during execution; all task content had already been embedded directly in each implementer subagent's dispatch prompt, so no implementation work was affected.
