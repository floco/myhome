<!-- packages/editor/src/lib/components/DatePicker.svelte -->
<script lang="ts">
  import { _, locale } from "svelte-i18n";

  interface Props {
    value?: string;
    placeholder?: string;
  }
  let { value = $bindable(""), placeholder }: Props = $props();

  let open = $state(false);
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());

  function monthNames(loc: string): string[] {
    return Array.from({ length: 12 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { month: "long" }).format(new Date(2000, i, 1))
    );
  }

  function dayHeaders(loc: string): string[] {
    // Jan 7 2024 was a Sunday, matching Date#getDay()'s 0=Sunday convention
    // used below to index into this array.
    return Array.from({ length: 7 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { weekday: "short" }).format(new Date(2024, 0, 7 + i))
    );
  }

  const MONTH_NAMES = $derived(monthNames($locale ?? "en"));
  const DAY_HEADERS = $derived(dayHeaders($locale ?? "en"));
  const effectivePlaceholder = $derived(placeholder ?? $_('datePicker.placeholder'));

  const monthGrid = $derived((() => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < firstDay; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  })());

  function displayValue(): string {
    if (!value) return "";
    const [y, m, d] = value.split("-");
    return `${d} ${MONTH_NAMES[parseInt(m) - 1]} ${y}`;
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

  function selectDay(day: number): void {
    const mm = String(viewMonth + 1).padStart(2, "0");
    const dd = String(day).padStart(2, "0");
    value = `${viewYear}-${mm}-${dd}`;
    open = false;
  }

  function prevMonth(): void {
    if (viewMonth === 0) { viewMonth = 11; viewYear--; } else viewMonth--;
  }

  function nextMonth(): void {
    if (viewMonth === 11) { viewMonth = 0; viewYear++; } else viewMonth++;
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
</script>

<svelte:window onclick={handleWindowClick} />

<div class="dp-wrap">
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="dp-field" onclick={() => { open = !open; }}>
    <span class="dp-text">{displayValue() || effectivePlaceholder}</span>
    <span class="dp-icon">📅</span>
  </div>

  {#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="dp-calendar" onclick={(e) => e.stopPropagation()}>
      <div class="dp-header">
        <button class="dp-nav" onclick={prevMonth}>‹</button>
        <span class="dp-month-label">{MONTH_NAMES[viewMonth]} {viewYear}</span>
        <button class="dp-nav" onclick={nextMonth}>›</button>
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
              class="dp-cell"
              class:dp-selected={isSelected(day)}
              class:dp-today={isToday(day)}
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
    padding: 8px 12px; border-radius: var(--radius-md); cursor: pointer;
    font-size: 13px; font-family: var(--font-sans); min-width: 160px;
    user-select: none; box-sizing: border-box;
  }
  .dp-field:hover { border-color: var(--accent); }
  .dp-text { flex: 1; }
  .dp-icon { font-size: 13px; flex-shrink: 0; }

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
</style>
