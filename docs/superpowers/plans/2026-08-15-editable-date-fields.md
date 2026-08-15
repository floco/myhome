# Editable Date Fields with Year-Jump Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let every date field in the app be edited either by typing a date directly or by picking one from the calendar popup, and let the calendar popup jump quickly to a distant year via a year-grid view, instead of only stepping month-by-month.

**Architecture:** All behavior lives in the single shared `DatePicker.svelte` component (moved from `packages/editor/src/lib/components/` to `packages/editor/src/lib/components/ui/` alongside the other generic primitives). The read-only display `<span>` becomes a real `<input type="text">` bound to a local edit buffer that is parsed against the same locale format used for display; the popup calendar gains a second "years" view reachable by clicking the month/year label. The two remaining call sites that used a native `<input type="date">` are migrated onto the same component so every date field in the app behaves identically.

**Tech Stack:** Svelte 5 (runes: `$state`, `$derived`, `$effect`, `$bindable`), TypeScript, `svelte-i18n`, Vitest + `@testing-library`-free DOM mounting via `svelte`'s `mount`/`unmount`/`flushSync`, CSS custom properties from `packages/editor/src/lib/theme.css`.

## Global Constraints

- Follow existing Svelte 5 runes conventions already used in `DatePicker.svelte` (no new state-management library).
- All new user-facing strings must go through `svelte-i18n` (`$_(...)`) if any are added; this plan adds none (existing `datePicker.placeholder` key is reused, no new UI copy is introduced).
- All new styling must use existing CSS custom properties from `theme.css` (`--surface`, `--surface-alt`, `--surface-hover`, `--border`, `--text`, `--text-muted`, `--text-faint`, `--accent`, `--accent-contrast`, `--radius-md`, `--shadow-md`, `--font-sans`) — no hardcoded colors.
- Test command for this package: `cd packages/editor && npx vitest run <path>` (or `npm run test` for the whole suite).

---

### Task 1: Move `DatePicker.svelte` into `ui/` and repoint all imports

**Files:**
- Move: `packages/editor/src/lib/components/DatePicker.svelte` → `packages/editor/src/lib/components/ui/DatePicker.svelte`
- Modify: `packages/editor/src/lib/components/WorkModal.svelte:9`
- Modify: `packages/editor/src/lib/components/ChoreEditModal.svelte:12`
- Modify: `packages/editor/src/lib/components/ChoreCompleteModal.svelte:7`
- Modify: `packages/editor/src/lib/components/TaskModal.svelte:9`
- Modify: `packages/editor/src/lib/components/InventoryModal.svelte:7`
- Modify: `packages/editor/src/lib/components/InsuranceModal.svelte:9`
- Modify: `packages/editor/src/lib/components/CostsEntryModal.svelte:10`
- Modify: `packages/editor/test/DatePicker.test.ts:3`

**Interfaces:**
- Produces: `DatePicker.svelte` at its new path `packages/editor/src/lib/components/ui/DatePicker.svelte`, with the exact same public props as before (`value` bindable string, `placeholder?: string`, `max?: string`, `compact?: boolean`). No behavior changes in this task.

- [ ] **Step 1: Move the file with git**

```bash
cd /projects/myhome
git mv packages/editor/src/lib/components/DatePicker.svelte packages/editor/src/lib/components/ui/DatePicker.svelte
```

- [ ] **Step 2: Fix the moved file's internal import path and header comment**

In `packages/editor/src/lib/components/ui/DatePicker.svelte`, change:

```svelte
<!-- packages/editor/src/lib/components/DatePicker.svelte -->
<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import { getWeekStart, getDateFormat } from "../localization";
```

to:

```svelte
<!-- packages/editor/src/lib/components/ui/DatePicker.svelte -->
<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import { getWeekStart, getDateFormat } from "../../localization";
```

- [ ] **Step 3: Update the test file's import path**

In `packages/editor/test/DatePicker.test.ts`, change:

```ts
import DatePicker from "../src/lib/components/DatePicker.svelte";
```

to:

```ts
import DatePicker from "../src/lib/components/ui/DatePicker.svelte";
```

- [ ] **Step 4: Update the 7 modal call sites**

In each of these files, change the import line from `"./DatePicker.svelte"` to `"./ui/DatePicker.svelte"` (the surrounding line content — e.g. `  import DatePicker from "./DatePicker.svelte";` — is otherwise identical in each file):

- `packages/editor/src/lib/components/WorkModal.svelte:9`
- `packages/editor/src/lib/components/ChoreEditModal.svelte:12`
- `packages/editor/src/lib/components/ChoreCompleteModal.svelte:7`
- `packages/editor/src/lib/components/TaskModal.svelte:9`
- `packages/editor/src/lib/components/InventoryModal.svelte:7`
- `packages/editor/src/lib/components/InsuranceModal.svelte:9`
- `packages/editor/src/lib/components/CostsEntryModal.svelte:10`

Result for each: `  import DatePicker from "./ui/DatePicker.svelte";`

- [ ] **Step 5: Run the full frontend test suite to confirm nothing broke**

```bash
cd /projects/myhome/packages/editor && npx vitest run
```

Expected: all tests pass (same count as before the move — this is a pure rename, no behavior change).

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add -A packages/editor/src/lib/components/DatePicker.svelte packages/editor/src/lib/components/ui/DatePicker.svelte \
  packages/editor/src/lib/components/WorkModal.svelte packages/editor/src/lib/components/ChoreEditModal.svelte \
  packages/editor/src/lib/components/ChoreCompleteModal.svelte packages/editor/src/lib/components/TaskModal.svelte \
  packages/editor/src/lib/components/InventoryModal.svelte packages/editor/src/lib/components/InsuranceModal.svelte \
  packages/editor/src/lib/components/CostsEntryModal.svelte packages/editor/test/DatePicker.test.ts
git commit -m "Move DatePicker into ui/ alongside other shared primitives"
```

---

### Task 2: Editable text input in `DatePicker`

**Files:**
- Modify: `packages/editor/src/lib/components/ui/DatePicker.svelte` (full rewrite of the trigger markup, plus new parsing logic)
- Modify: `packages/editor/test/DatePicker.test.ts` (full rewrite: existing tests updated for the new markup, new "manual entry" tests added)

**Interfaces:**
- Consumes: nothing new — same props as Task 1 (`value` bindable ISO `YYYY-MM-DD` string, `placeholder?`, `max?`, `compact?`).
- Produces: the field now renders `input.dp-input` (a real text input holding the formatted display string) and `button.dp-icon-btn` (toggles the calendar popup) inside `.dp-field`, replacing the old read-only `span.dp-text`. `.dp-field` itself is no longer a click target for opening the popup. This new markup is what Task 3 and Task 4 build on.

- [ ] **Step 1: Rewrite `packages/editor/test/DatePicker.test.ts`**

Replace the entire file with:

```ts
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import DatePicker from "../src/lib/components/ui/DatePicker.svelte";

describe("DatePicker week start", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("defaults to a Sunday-first grid", () => {
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    const headers = [...target.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Sun");
    unmount(app);
  });

  it("starts the grid on Monday when the week-start preference is Monday", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    const headers = [...target.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Mon");
    unmount(app);
  });

  it("shifts the leading blank cells to match a Monday-first grid", () => {
    // January 2024: the 1st is a Monday. Sunday-first grid needs 1 leading blank
    // (Jan 1 falls in column index 1); Monday-first grid needs 0 leading blanks.
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: { value: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    const cells = [...target.querySelectorAll(".dp-cell")];
    expect(cells[0].classList.contains("dp-empty")).toBe(false);
    expect(cells[0].textContent).toBe("1");
    unmount(app);
  });
});

describe("DatePicker max", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("disables and ignores clicks on days after max", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();

    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day20 = cells.find((c) => c.textContent === "20")!;
    expect(day20.disabled).toBe(true);

    day20.click();
    flushSync();

    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toContain("10");
    unmount(app);
  });

  it("still allows selecting a day at or before max", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();

    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day15 = cells.find((c) => c.textContent === "15")!;
    expect(day15.disabled).toBe(false);

    day15.click();
    flushSync();

    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toContain("15");
    unmount(app);
  });
});

describe("DatePicker date format", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("displays DMY when the Settings date format is DMY", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "DMY", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toBe("05/07/2026");
    unmount(app);
  });

  it("displays MDY when the Settings date format is MDY", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "MDY", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toBe("07/05/2026");
    unmount(app);
  });

  it("displays ISO when the Settings date format is ISO", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "ISO", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toBe("2026-07-05");
    unmount(app);
  });

  it("falls back to the en-locale default (MDY) when no override is set", () => {
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toBe("07/05/2026");
    unmount(app);
  });

  it("displays LONG when the Settings date format is explicitly LONG", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "LONG", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toBe("05 July 2026");
    unmount(app);
  });
});

describe("DatePicker compact", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("applies the compact class when the compact prop is set", () => {
    const app = mount(DatePicker, { target, props: { compact: true } });
    flushSync();
    expect(target.querySelector(".dp-field")!.classList.contains("compact")).toBe(true);
    unmount(app);
  });

  it("does not apply the compact class by default", () => {
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    expect(target.querySelector(".dp-field")!.classList.contains("compact")).toBe(false);
    unmount(app);
  });
});

describe("DatePicker manual entry", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("commits a valid typed date on blur", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = target.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "03/05/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("03/05/2024");
    unmount(app);
  });

  it("commits a valid typed date on Enter", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = target.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "12/25/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();

    expect(input.value).toBe("12/25/2024");
    unmount(app);
  });

  it("reverts to the last valid value when the typed text is unparseable", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = target.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "not a date";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("01/10/2024");
    unmount(app);
  });

  it("reverts without committing on Escape", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = target.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "12/25/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    flushSync();

    expect(input.value).toBe("01/10/2024");
    unmount(app);
  });

  it("rejects a typed date beyond max and reverts", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();

    const input = target.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "01/20/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("01/10/2024");
    unmount(app);
  });

  it("parses a typed DMY date when the Settings date format is DMY", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "DMY", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = target.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "25/12/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("25/12/2024");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run the tests to confirm the new/updated ones fail against the current markup**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/DatePicker.test.ts
```

Expected: FAIL — `.dp-icon-btn` and `.dp-input` don't exist yet in the current component.

- [ ] **Step 3: Rewrite `packages/editor/src/lib/components/ui/DatePicker.svelte`**

Replace the entire file with:

```svelte
<!-- packages/editor/src/lib/components/ui/DatePicker.svelte -->
<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import { getWeekStart, getDateFormat } from "../../localization";

  interface Props {
    value?: string;
    placeholder?: string;
    max?: string;
    compact?: boolean;
  }
  let { value = $bindable(""), placeholder, max, compact = false }: Props = $props();

  let open = $state(false);
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());
  let editing = $state(false);
  let editText = $state("");

  function monthNames(loc: string): string[] {
    return Array.from({ length: 12 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { month: "long" }).format(new Date(2000, i, 1))
    );
  }

  function dayHeaders(loc: string, weekStart: number): string[] {
    // Jan 7 2024 was a Sunday, matching Date#getDay()'s 0=Sunday convention
    // used below to index into this array.
    const sundayFirst = Array.from({ length: 7 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { weekday: "short" }).format(new Date(2024, 0, 7 + i))
    );
    return [...sundayFirst.slice(weekStart), ...sundayFirst.slice(0, weekStart)];
  }

  const MONTH_NAMES = $derived(monthNames($locale ?? "en"));
  const weekStart = $derived(getWeekStart());
  const DAY_HEADERS = $derived(dayHeaders($locale ?? "en", weekStart));
  const effectivePlaceholder = $derived(placeholder ?? $_('datePicker.placeholder'));

  const monthGrid = $derived((() => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const leading = (firstDay - weekStart + 7) % 7;
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < leading; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  })());

  function displayValue(): string {
    if (!value) return "";
    const [y, m, d] = value.split("-");
    const format = getDateFormat();
    if (format === "MDY") return `${m}/${d}/${y}`;
    if (format === "DMY") return `${d}/${m}/${y}`;
    if (format === "ISO") return `${y}-${m}-${d}`;
    return `${d} ${MONTH_NAMES[parseInt(m) - 1]} ${y}`;
  }

  function isValidCalendarDate(y: number, m: number, d: number): boolean {
    if (m < 1 || m > 12 || d < 1) return false;
    const dt = new Date(y, m - 1, d);
    return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
  }

  function parseDisplayValue(text: string): string | null {
    const trimmed = text.trim();
    if (!trimmed) return null;
    const format = getDateFormat();
    let y: number, m: number, d: number;

    if (format === "MDY" || format === "DMY") {
      const match = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
      if (!match) return null;
      if (format === "MDY") { m = parseInt(match[1]); d = parseInt(match[2]); }
      else { d = parseInt(match[1]); m = parseInt(match[2]); }
      y = parseInt(match[3]);
    } else if (format === "ISO") {
      const match = trimmed.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
      if (!match) return null;
      y = parseInt(match[1]); m = parseInt(match[2]); d = parseInt(match[3]);
    } else {
      const match = trimmed.match(/^(\d{1,2})\s+(\S+)\s+(\d{4})$/);
      if (!match) return null;
      d = parseInt(match[1]);
      y = parseInt(match[3]);
      const monthIndex = MONTH_NAMES.findIndex((n) => n.toLowerCase() === match[2].toLowerCase());
      if (monthIndex === -1) return null;
      m = monthIndex + 1;
    }

    if (!isValidCalendarDate(y, m, d)) return null;
    const iso = `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    if (max && iso > max) return null;
    return iso;
  }

  function isSelected(day: number): boolean {
    if (!value) return false;
    const [y, m, d] = value.split("-");
    return parseInt(y) === viewYear && parseInt(m) === viewMonth + 1 && parseInt(d) === day;
  }

  function isToday(day: number): boolean {
    const t = new Date();
    return t.getFullYear() === viewYear && t.getMonth() === viewMonth && t.getDate() === day;
  }

  function cellIso(day: number): string {
    const mm = String(viewMonth + 1).padStart(2, "0");
    const dd = String(day).padStart(2, "0");
    return `${viewYear}-${mm}-${dd}`;
  }

  function isDisabled(day: number): boolean {
    return !!max && cellIso(day) > max;
  }

  function selectDay(day: number): void {
    if (isDisabled(day)) return;
    value = cellIso(day);
    open = false;
  }

  function prevMonth(): void {
    if (viewMonth === 0) { viewMonth = 11; viewYear--; } else viewMonth--;
  }

  function nextMonth(): void {
    if (viewMonth === 11) { viewMonth = 0; viewYear++; } else viewMonth++;
  }

  function toggleOpen(): void {
    open = !open;
  }

  function handleFocus(): void {
    editText = displayValue();
    editing = true;
  }

  function commitEdit(): void {
    const parsed = parseDisplayValue(editText);
    if (parsed !== null) value = parsed;
    editing = false;
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter") {
      (e.target as HTMLInputElement).blur();
    } else if (e.key === "Escape") {
      editText = displayValue();
      (e.target as HTMLInputElement).blur();
    }
  }

  function handleWindowClick(e: MouseEvent): void {
    if (!(e.target as HTMLElement).closest?.(".dp-wrap")) open = false;
  }

  $effect(() => {
    if (value) {
      const parts = value.split("-");
      if (parts.length === 3) {
        viewYear = parseInt(parts[0]);
        viewMonth = parseInt(parts[1]) - 1;
      }
    }
  });

  $effect(() => {
    if (!editing) editText = displayValue();
  });
</script>

<svelte:window onclick={handleWindowClick} />

<div class="dp-wrap">
  <div class="dp-field" class:compact>
    <input
      class="dp-input"
      type="text"
      bind:value={editText}
      placeholder={effectivePlaceholder}
      onfocus={handleFocus}
      onblur={commitEdit}
      onkeydown={handleKeydown}
    />
    <button type="button" class="dp-icon-btn" onclick={toggleOpen}>
      <span class="dp-icon">📅</span>
    </button>
  </div>

  {#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="dp-calendar" onclick={(e) => e.stopPropagation()}>
      <div class="dp-header">
        <button type="button" class="dp-nav" onclick={prevMonth}>‹</button>
        <span class="dp-month-label">{MONTH_NAMES[viewMonth]} {viewYear}</span>
        <button type="button" class="dp-nav" onclick={nextMonth}>›</button>
      </div>
      <div class="dp-grid">
        {#each DAY_HEADERS as h}
          <div class="dp-dh">{h}</div>
        {/each}
        {#each monthGrid as day}
          {#if day === null}
            <div class="dp-cell dp-empty"></div>
          {:else}
            <button
              type="button"
              class="dp-cell"
              class:dp-selected={isSelected(day)}
              class:dp-today={isToday(day)}
              disabled={isDisabled(day)}
              onclick={() => selectDay(day)}
            >{day}</button>
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .dp-wrap { position: relative; display: inline-block; width: 100%; }

  .dp-field {
    display: flex; align-items: center; gap: 6px;
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md);
    font-size: 13px; font-family: var(--font-sans); min-width: 160px;
    box-sizing: border-box;
  }
  .dp-field.compact { min-width: 0; width: 100%; padding: 4px 8px; font-size: 11px; gap: 4px; }
  .dp-field.compact .dp-icon { font-size: 11px; }
  .dp-field:hover { border-color: var(--accent); }
  .dp-field:focus-within { border-color: var(--accent); }

  .dp-input {
    flex: 1; min-width: 0; background: none; border: none; color: var(--text);
    font-size: inherit; font-family: inherit; padding: 0;
  }
  .dp-input:focus { outline: none; }
  .dp-input::placeholder { color: var(--text-faint); }

  .dp-icon-btn {
    flex-shrink: 0; background: none; border: none; padding: 0; cursor: pointer;
    display: flex; align-items: center;
  }
  .dp-icon { font-size: 13px; }

  .dp-calendar {
    position: absolute; top: calc(100% + 4px); left: 0;
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md);
    padding: 10px; z-index: 300; box-shadow: var(--shadow-md);
    min-width: 220px;
  }

  .dp-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 8px;
  }
  .dp-nav {
    background: none; border: none; color: var(--text-muted); font-size: 16px;
    cursor: pointer; padding: 0 6px; line-height: 1;
  }
  .dp-nav:hover { color: var(--text); }
  .dp-month-label { font-size: 12px; color: var(--text); font-family: var(--font-sans); font-weight: 600; }

  .dp-grid {
    display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;
  }
  .dp-dh {
    text-align: center; font-size: 9px; color: var(--text-faint); padding: 2px 0;
    font-family: var(--font-sans);
  }
  .dp-cell {
    text-align: center; font-size: 11px; font-family: var(--font-sans);
    padding: 4px 2px; border-radius: 3px; cursor: pointer;
    background: none; border: none; color: var(--text-muted);
  }
  .dp-cell:hover:not(.dp-selected) { background: var(--surface-hover); color: var(--text); }
  .dp-empty { cursor: default; }
  .dp-today { color: var(--accent); font-weight: 600; }
  .dp-selected { background: var(--accent); color: var(--accent-contrast); font-weight: 600; }
  .dp-selected:hover { opacity: 0.85; }
  .dp-cell:disabled { color: var(--text-faint); cursor: default; opacity: 0.5; }
  .dp-cell:disabled:hover { background: none; color: var(--text-faint); }
</style>
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/DatePicker.test.ts
```

Expected: PASS (all tests, including the new "DatePicker manual entry" block).

- [ ] **Step 5: Typecheck**

```bash
cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json
```

Expected: no new errors from `DatePicker.svelte` (the `parseDisplayValue` branches must leave `y`/`m`/`d` definitely assigned on every path that doesn't return early).

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ui/DatePicker.svelte packages/editor/test/DatePicker.test.ts
git commit -m "Make DatePicker's date field editable by typing"
```

---

### Task 3: Year-grid navigation in the calendar popup

**Files:**
- Modify: `packages/editor/src/lib/components/ui/DatePicker.svelte`
- Modify: `packages/editor/test/DatePicker.test.ts`

**Interfaces:**
- Consumes: the `.dp-icon-btn`/`.dp-input` markup and `viewYear`/`viewMonth` state produced by Task 2.
- Produces: clicking `.dp-month-label` (now a `<button>`) switches the popup to a `.dp-year-grid` of `.dp-year-cell` buttons (12 per page); `.dp-nav` buttons in that view page by 12 years; clicking a `.dp-year-cell` returns to `.dp-grid` (the day view) with `viewYear` set to the clicked year and `viewMonth` unchanged.

- [ ] **Step 1: Append year-grid tests to `packages/editor/test/DatePicker.test.ts`**

Add this new `describe` block at the end of the file:

```ts
describe("DatePicker year grid", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  function openCalendar(): void {
    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
  }

  it("switches to a 12-year grid when the month/year label is clicked", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();

    (target.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();

    const years = [...target.querySelectorAll(".dp-year-cell")].map((c) => c.textContent);
    expect(years).toEqual(["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027"]);
    const selected = target.querySelector(".dp-year-cell.dp-selected");
    expect(selected?.textContent).toBe("2024");
    unmount(app);
  });

  it("pages the year grid forward and backward by 12 years", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();
    (target.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();

    const [prevBtn, nextBtn] = [...target.querySelectorAll(".dp-nav")] as HTMLButtonElement[];
    nextBtn.click();
    flushSync();
    let years = [...target.querySelectorAll(".dp-year-cell")].map((c) => c.textContent);
    expect(years[0]).toBe("2028");

    prevBtn.click();
    flushSync();
    years = [...target.querySelectorAll(".dp-year-cell")].map((c) => c.textContent);
    expect(years[0]).toBe("2016");
    unmount(app);
  });

  it("selecting a year returns to the day grid for that year, keeping the month", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();
    (target.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();

    const yearCell = [...target.querySelectorAll(".dp-year-cell")].find((c) => c.textContent === "2018") as HTMLButtonElement;
    yearCell.click();
    flushSync();

    expect(target.querySelector(".dp-grid")).not.toBeNull();
    expect(target.querySelector(".dp-year-grid")).toBeNull();
    expect(target.querySelector(".dp-month-label")!.textContent).toBe("June 2018");
    unmount(app);
  });

  it("reopening the calendar always starts on the day view", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();
    (target.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();
    expect(target.querySelector(".dp-year-grid")).not.toBeNull();

    // close (click icon again) and reopen
    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    openCalendar();

    expect(target.querySelector(".dp-grid")).not.toBeNull();
    expect(target.querySelector(".dp-year-grid")).toBeNull();
    unmount(app);
  });
});
```

- [ ] **Step 2: Run the tests to confirm the new ones fail**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/DatePicker.test.ts
```

Expected: FAIL — `.dp-month-label` is currently a `<span>` (not clickable) and `.dp-year-grid`/`.dp-year-cell` don't exist.

- [ ] **Step 3: Add year-grid state and handlers to the script block**

In `packages/editor/src/lib/components/ui/DatePicker.svelte`, add a `view` state and `yearGridStart` state near the other `$state` declarations:

```ts
  let open = $state(false);
  let view = $state<"days" | "years">("days");
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());
  let yearGridStart = $state(Math.floor(new Date().getFullYear() / 12) * 12);
  let editing = $state(false);
  let editText = $state("");
```

Add a derived list of the 12 years shown on the current page, next to `monthGrid`:

```ts
  const yearGridCells = $derived(Array.from({ length: 12 }, (_unused, i) => yearGridStart + i));
```

Add the year-grid handlers, and reset `view` to `"days"` whenever the popup is (re)opened, next to `prevMonth`/`nextMonth`:

```ts
  function openYearGrid(): void {
    yearGridStart = Math.floor(viewYear / 12) * 12;
    view = "years";
  }

  function selectYear(year: number): void {
    viewYear = year;
    view = "days";
  }

  function prevDecade(): void { yearGridStart -= 12; }
  function nextDecade(): void { yearGridStart += 12; }

  function toggleOpen(): void {
    if (!open) view = "days";
    open = !open;
  }
```

Remove the old `toggleOpen` (`function toggleOpen(): void { open = !open; }`) added in Task 2 — it's replaced by the version above.

- [ ] **Step 4: Update the calendar popup markup**

Replace the `{#if open}` block's contents in the template with a `view` switch:

```svelte
  {#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="dp-calendar" onclick={(e) => e.stopPropagation()}>
      {#if view === "days"}
        <div class="dp-header">
          <button type="button" class="dp-nav" onclick={prevMonth}>‹</button>
          <button type="button" class="dp-month-label" onclick={openYearGrid}>{MONTH_NAMES[viewMonth]} {viewYear}</button>
          <button type="button" class="dp-nav" onclick={nextMonth}>›</button>
        </div>
        <div class="dp-grid">
          {#each DAY_HEADERS as h}
            <div class="dp-dh">{h}</div>
          {/each}
          {#each monthGrid as day}
            {#if day === null}
              <div class="dp-cell dp-empty"></div>
            {:else}
              <button
                type="button"
                class="dp-cell"
                class:dp-selected={isSelected(day)}
                class:dp-today={isToday(day)}
                disabled={isDisabled(day)}
                onclick={() => selectDay(day)}
              >{day}</button>
            {/if}
          {/each}
        </div>
      {:else}
        <div class="dp-header">
          <button type="button" class="dp-nav" onclick={prevDecade}>‹</button>
          <span class="dp-month-label">{yearGridStart}–{yearGridStart + 11}</span>
          <button type="button" class="dp-nav" onclick={nextDecade}>›</button>
        </div>
        <div class="dp-year-grid">
          {#each yearGridCells as y}
            <button
              type="button"
              class="dp-year-cell"
              class:dp-selected={y === viewYear}
              onclick={() => selectYear(y)}
            >{y}</button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
```

Note `.dp-month-label` is now a `<button>` in the days-view header (was a `<span>`) — this is what Step 3 of Task 2 originally rendered as a span; here it becomes clickable.

- [ ] **Step 5: Add year-grid CSS**

In the `<style>` block, update `.dp-month-label` to look right as a button (remove default button chrome) and add the year-grid rules, right after the existing `.dp-cell:disabled:hover` rule:

```css
  .dp-month-label {
    background: none; border: none; cursor: pointer;
    font-size: 12px; color: var(--text); font-family: var(--font-sans); font-weight: 600;
  }
```

(this replaces the old `.dp-month-label` rule, which lacked `background`/`border`/`cursor` since it used to be a plain `<span>`)

```css
  .dp-year-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; }
  .dp-year-cell {
    text-align: center; font-size: 12px; font-family: var(--font-sans);
    padding: 8px 2px; border-radius: 3px; cursor: pointer;
    background: none; border: none; color: var(--text-muted);
  }
  .dp-year-cell:hover:not(.dp-selected) { background: var(--surface-hover); color: var(--text); }
```

- [ ] **Step 6: Run the tests to confirm they pass**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/DatePicker.test.ts
```

Expected: PASS (all tests, including the new "DatePicker year grid" block).

- [ ] **Step 7: Typecheck**

```bash
cd /projects/myhome/packages/editor && npx svelte-check --tsconfig ./tsconfig.json
```

Expected: no new errors.

- [ ] **Step 8: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/ui/DatePicker.svelte packages/editor/test/DatePicker.test.ts
git commit -m "Add year-grid navigation to DatePicker's calendar popup"
```

---

### Task 4: Migrate the two native `type="date"` stragglers onto `DatePicker`

**Files:**
- Modify: `packages/editor/src/lib/components/NewChoreModal.svelte`
- Modify: `packages/editor/src/lib/components/settings/SettingsActivityLog.svelte`
- Modify: `packages/editor/test/NewChoreModal.test.ts`
- Modify: `packages/editor/test/SettingsActivityLog.test.ts`

**Interfaces:**
- Consumes: `DatePicker` from `packages/editor/src/lib/components/ui/DatePicker.svelte` (Tasks 1-3), same bindable `value` prop.
- Produces: no new interfaces — this task only removes the last two native `<input type="date">`/`<Input type="date">` usages in the frontend.

- [ ] **Step 1: Add a failing test to `packages/editor/test/NewChoreModal.test.ts`**

Add this test inside the existing `describe("NewChoreModal", ...)` block:

```ts
  it("uses the shared DatePicker for the first-due date instead of a native date input", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(NewChoreModal, { target, props: { open: true, store, onclose: vi.fn() } });
    flushSync();

    expect(target.querySelector('input[type="date"]')).toBeNull();
    expect(target.querySelector(".dp-field")).not.toBeNull();

    unmount(app);
  });
```

- [ ] **Step 2: Add a failing test to `packages/editor/test/SettingsActivityLog.test.ts`**

Add this test inside the existing `describe("SettingsActivityLog", ...)` block (it can reuse the `target`/`fetchMock` set up in the shared `beforeEach`):

```ts
  it("uses the shared DatePicker for the from/to filters instead of native date inputs", async () => {
    const app = mount(SettingsActivityLog, { target });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.querySelectorAll('input[type="date"]').length).toBe(0);
    expect(target.querySelectorAll(".dp-field").length).toBe(2);

    unmount(app);
  });
```

- [ ] **Step 3: Run both test files to confirm they fail**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/NewChoreModal.test.ts test/SettingsActivityLog.test.ts
```

Expected: FAIL on the two new tests — both components still render native `type="date"` inputs.

- [ ] **Step 4: Migrate `NewChoreModal.svelte`**

Add the import, alongside the other component imports at the top of `packages/editor/src/lib/components/NewChoreModal.svelte`:

```ts
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import ScheduleAnchorPicker from "./ui/ScheduleAnchorPicker.svelte";
  import DatePicker from "./ui/DatePicker.svelte";
  import ScheduleEditor from "./ScheduleEditor.svelte";
```

Replace the date field (`NewChoreModal.svelte:127-130`):

```svelte
    <div class="field">
      <label for="chore-due">{$_('chores.newModal.firstDue')}</label>
      <input id="chore-due" type="date" class="native-input" bind:value={nextDue} />
    </div>
```

with:

```svelte
    <div class="field">
      <label>{$_('chores.newModal.firstDue')}
        <DatePicker bind:value={nextDue} />
      </label>
    </div>
```

Remove the now-dead CSS rule for the native date input (`NewChoreModal.svelte:160`):

```css
  input[type="date"].native-input { width: 160px; }
```

(delete this line; the surrounding `.native-input` rules stay — they're still used by the name and quick-add text inputs)

- [ ] **Step 5: Migrate `SettingsActivityLog.svelte`**

Replace the `Input` import with `DatePicker` in `packages/editor/src/lib/components/settings/SettingsActivityLog.svelte`:

```svelte
  import { _ } from "svelte-i18n";
  import { formatDateTime } from "../../dateFormat";
  import DatePicker from "../ui/DatePicker.svelte";
  import Button from "../ui/Button.svelte";
  import Card from "../ui/Card.svelte";
  import { homesStore } from "../../homesStore.svelte";
```

Replace the two filter fields:

```svelte
      <div class="modal-field">
        <span class="modal-label">{$_('settings.activityLog.from')}</span>
        <Input type="date" bind:value={activitySinceFilter} />
      </div>
      <div class="modal-field">
        <span class="modal-label">{$_('settings.activityLog.to')}</span>
        <Input type="date" bind:value={activityUntilFilter} />
      </div>
```

with:

```svelte
      <div class="modal-field">
        <span class="modal-label">{$_('settings.activityLog.from')}</span>
        <DatePicker bind:value={activitySinceFilter} />
      </div>
      <div class="modal-field">
        <span class="modal-label">{$_('settings.activityLog.to')}</span>
        <DatePicker bind:value={activityUntilFilter} />
      </div>
```

- [ ] **Step 6: Run both test files to confirm they pass**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/NewChoreModal.test.ts test/SettingsActivityLog.test.ts
```

Expected: PASS.

- [ ] **Step 7: Run the full frontend test suite**

```bash
cd /projects/myhome/packages/editor && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/NewChoreModal.svelte \
  packages/editor/src/lib/components/settings/SettingsActivityLog.svelte \
  packages/editor/test/NewChoreModal.test.ts packages/editor/test/SettingsActivityLog.test.ts
git commit -m "Migrate NewChoreModal and SettingsActivityLog off native date inputs onto DatePicker"
```

---

## Manual verification (after all tasks)

Automated tests cover parsing/reverting/year-navigation logic, but this is a visual/interactive feature — run the dev server and check by hand before considering this done:

- [ ] Open any modal with a date field (e.g. new/edit chore, add work, add insurance policy). Confirm you can click into the date field and type a date in the format shown, and that it commits on blur/Enter.
- [ ] Type garbage into a date field and blur/Tab away — confirm it reverts to the previous value instead of accepting bad input.
- [ ] Click the calendar icon, click the month/year label, confirm the year grid appears, page a few times with «/», and click a year — confirm it lands back on the day grid for that year with the month preserved.
- [ ] Check both light and dark theme for visual consistency (`--surface`/`--border`/`--accent` tokens should already handle this automatically).
- [ ] Check the `compact` variant (used in floor-plan pin popups, e.g. a cost-category pin) still looks reasonable with the new input+icon layout.
- [ ] Confirm the New Chore modal's "first due" field and Settings → Activity Log's from/to filters now show the same calendar-icon picker as everywhere else, not a native browser date input.
