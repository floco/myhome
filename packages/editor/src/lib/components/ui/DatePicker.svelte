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
  let view = $state<"days" | "years">("days");
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());
  let yearGridStart = $state(Math.floor(new Date().getFullYear() / 12) * 12);
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

  const yearGridCells = $derived(Array.from({ length: 12 }, (_unused, i) => yearGridStart + i));

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
  .dp-month-label {
    background: none; border: none; cursor: pointer;
    font-size: 12px; color: var(--text); font-family: var(--font-sans); font-weight: 600;
  }

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

  .dp-year-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; }
  .dp-year-cell {
    text-align: center; font-size: 12px; font-family: var(--font-sans);
    padding: 8px 2px; border-radius: 3px; cursor: pointer;
    background: none; border: none; color: var(--text-muted);
  }
  .dp-year-cell:hover:not(.dp-selected) { background: var(--surface-hover); color: var(--text); }
</style>
