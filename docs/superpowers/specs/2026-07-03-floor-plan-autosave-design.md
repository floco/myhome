# Floor Plan Autosave

**Date:** 2026-07-03  
**Status:** Approved

## Problem

Users forget to click the manual 💾 save button on the floor plan editor, risking loss of work.

## Goal

Automatically save the floor plan 5 seconds after the last edit, with a visible dirty indicator and Ctrl+S for immediate save.

## Non-goals

- Autosave for any module other than the floor plan (`houseStore`)
- Conflict resolution or version history beyond the existing undo stack
- Offline/local-storage fallback

---

## Architecture

Three focused changes, no new files.

### 1. `houseStore.svelte.ts` — generation counter

Add two private `$state` integers:

```ts
let generation = $state(0);
let savedGeneration = $state(0);
```

**Increment `generation`** at the top of every mutation that already calls `saveSnapshot()`:
`addFloor`, `removeFloor`, `renameFloor`, `addWall`, `removeWall`, `moveSharedPoint` (only when `!opts?.skipHistory`), `addOpening`, `removeOpening`, `updateOpening` (only when `!opts?.skipHistory`), `updateRoom`.

Also increment in `undo()` and `redo()` (after applying state).

**Reset both on load** — at the end of `init()`, after applying the loaded state:
```ts
generation = 0;
savedGeneration = 0;
```

**Mark clean on save** — at the end of `save()`, after the successful fetch:
```ts
savedGeneration = generation;
```

**New exported getters:**
```ts
get isDirty() { return generation !== savedGeneration; },
get generation() { return generation; },
```

`isDirty` is the public API consumers use. `generation` is exposed so `$effect` in App.svelte can declare a reactive dependency on it without needing to call `isDirty` inside the effect.

### 2. `App.svelte` — debounced autosave + Ctrl+S

**Debounced autosave effect** (added in the `<script>` block alongside other `$effect` calls):

```ts
let autosaveTimer: ReturnType<typeof setTimeout> | null = null;

$effect(() => {
  const _gen = floorStore.generation; // reactive dependency
  if (!floorStore.loaded || !floorStore.isDirty || !homesStore.activeHomeId) return;
  if (autosaveTimer) clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => {
    autosaveTimer = null;
    handleSave();
  }, 5000);
  return () => {
    if (autosaveTimer) { clearTimeout(autosaveTimer); autosaveTimer = null; }
  };
});
```

The cleanup function runs when the effect re-fires or the component unmounts, cancelling any pending timer.

**Ctrl+S** — add to the existing `handleKeydown` function, before other shortcuts:

```ts
if (event.ctrlKey && event.key === "s") {
  event.preventDefault();
  if (isFloorPlan) handleSave();
  return;
}
```

### 3. Save button — dirty dot indicator

The save button already has `class:saved` and `class:save-error`. Add `class:dirty`:

```svelte
<button
  class="icon-btn save-btn"
  class:saved={saveStatus === "saved"}
  class:save-error={saveStatus === "error"}
  class:dirty={floorStore.isDirty && saveStatus === "idle"}
  ...
>{saveIcon}</button>
```

Add CSS for the dot using a `::after` pseudo-element:

```css
.icon-btn.save-btn.dirty::after {
  content: '';
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  pointer-events: none;
}
```

The save button needs `position: relative` to anchor the dot — add that to `.icon-btn` or `.save-btn` specifically.

---

## Behaviour summary

| Scenario | Result |
|---|---|
| Edit walls/openings/rooms/floors | `isDirty = true`, dot appears, 5s timer starts |
| Another edit within 5s | Timer resets to 5s from latest edit |
| 5s with no further edits | Autosave fires; on success dot disappears, ✓ flashes 2s |
| Ctrl+S at any time | Immediate save, timer cancelled |
| Manual 💾 click | Same as Ctrl+S |
| Undo/redo | Also dirty (generation increments); autosave triggers |
| Switch home | `init()` resets both counters; starts clean |
| Save fails | `saveStatus = "error"`, dot remains (changes not persisted) |

---

## Testing

- `houseStore` unit tests: assert `isDirty` is false after init, true after mutation, false after `save()`, true after undo/redo
- `App.svelte` integration: no new test file needed; existing Canvas tests cover mutations; autosave timer can be tested by mocking `setTimeout` if desired
- Manual: edit a wall, wait 5s, observe ✓ flash and dot disappearing without clicking save
