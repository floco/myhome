<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import type { Chore, Assignment } from "../choreStore.svelte";
  import { displayName, isOverdue } from "../choreFormat";
  import { getWeekStart } from "../localization";

  interface Props {
    chores: Chore[];
    assignments: Assignment[];
    month: number; // 0-11
    year: number;
    roomFilter?: string;
    onmonthchange: (year: number, month: number) => void;
    onchoreclick: (choreId: string) => void;
  }
  let { chores, assignments, month, year, roomFilter = "", onmonthchange, onchoreclick }: Props = $props();

  function monthNames(loc: string): string[] {
    return Array.from({ length: 12 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { month: "long" }).format(new Date(2000, i, 1))
    );
  }

  function dayHeaders(loc: string, weekStart: number): string[] {
    // Jan 7 2024 was a Sunday, matching Date#getDay()'s 0=Sunday convention.
    const sundayFirst = Array.from({ length: 7 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { weekday: "short" }).format(new Date(2024, 0, 7 + i))
    );
    return [...sundayFirst.slice(weekStart), ...sundayFirst.slice(0, weekStart)];
  }

  function localDateKey(iso: string): string {
    const d = new Date(iso);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  const MONTH_NAMES = $derived(monthNames($locale ?? "en"));
  const weekStart = $derived(getWeekStart());
  const DAY_HEADERS = $derived(dayHeaders($locale ?? "en", weekStart));
  const yearOptions = $derived(Array.from({ length: 21 }, (_unused, i) => year - 10 + i));

  const monthGrid = $derived((() => {
    const firstDay = new Date(year, month, 1).getDay();
    const leading = (firstDay - weekStart + 7) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < leading; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  })());

  interface DayEntry { key: string; choreId: string; emoji: string; label: string; overdue: boolean }

  const entriesByDate = $derived((() => {
    const choresById = new Map(chores.map((c) => [c.id, c]));
    const map = new Map<string, DayEntry[]>();
    for (const a of assignments) {
      const chore = choresById.get(a.choreId);
      if (!chore || !a.nextDueDate) continue;
      if (roomFilter && a.roomId !== roomFilter) continue;
      const key = localDateKey(a.nextDueDate);
      const list = map.get(key) ?? [];
      list.push({ key: a.id, choreId: chore.id, emoji: chore.emoji, label: displayName(chore), overdue: isOverdue(a.nextDueDate) });
      map.set(key, list);
    }
    for (const list of map.values()) list.sort((x, y) => x.label.localeCompare(y.label));
    return map;
  })());

  function cellIso(day: number): string {
    return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  function entriesFor(day: number): DayEntry[] {
    return entriesByDate.get(cellIso(day)) ?? [];
  }

  function isToday(day: number): boolean {
    const t = new Date();
    return t.getFullYear() === year && t.getMonth() === month && t.getDate() === day;
  }

  function prevMonth(): void {
    if (month === 0) onmonthchange(year - 1, 11);
    else onmonthchange(year, month - 1);
  }

  function nextMonth(): void {
    if (month === 11) onmonthchange(year + 1, 0);
    else onmonthchange(year, month + 1);
  }

  function goToday(): void {
    const t = new Date();
    onmonthchange(t.getFullYear(), t.getMonth());
  }
</script>

<div class="cal">
  <div class="cal-header">
    <button class="cal-nav cal-prev" onclick={prevMonth} aria-label={$_('chores.page.prevMonth')}>‹</button>
    <select class="cal-select" value={month} onchange={(e) => onmonthchange(year, parseInt((e.currentTarget as HTMLSelectElement).value))}>
      {#each MONTH_NAMES as name, i}
        <option value={i}>{name}</option>
      {/each}
    </select>
    <select class="cal-select" value={year} onchange={(e) => onmonthchange(parseInt((e.currentTarget as HTMLSelectElement).value), month)}>
      {#each yearOptions as y}
        <option value={y}>{y}</option>
      {/each}
    </select>
    <button class="cal-nav cal-next" onclick={nextMonth} aria-label={$_('chores.page.nextMonth')}>›</button>
    <button class="cal-today" onclick={goToday}>{$_('chores.page.today')}</button>
  </div>

  <div class="cal-daynames">
    {#each DAY_HEADERS as h}
      <div class="cal-dayname">{h}</div>
    {/each}
  </div>

  <div class="cal-grid">
    {#each monthGrid as cell}
      {#if cell === null}
        <div class="cal-cell cal-empty"></div>
      {:else}
        <div class="cal-cell" class:cal-today={isToday(cell)}>
          <div class="cal-daynum">{cell}</div>
          <div class="cal-entries">
            {#each entriesFor(cell) as entry (entry.key)}
              <button class="cal-chip" class:overdue={entry.overdue} title={entry.label} onclick={() => onchoreclick(entry.choreId)}>
                <span class="chip-emoji">{entry.emoji}</span><span class="chip-label">{entry.label}</span>
              </button>
            {/each}
          </div>
        </div>
      {/if}
    {/each}
  </div>
</div>

<style>
  .cal { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }

  .cal-header {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--border); flex-shrink: 0; flex-wrap: wrap;
  }
  .cal-nav {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    border-radius: var(--radius-sm); width: 32px; height: 32px; font-size: 16px; cursor: pointer;
  }
  .cal-nav:hover { background: var(--surface-hover); }
  .cal-select {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 6px 10px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans); cursor: pointer;
  }
  .cal-select:focus { outline: none; border-color: var(--accent); }
  .cal-today {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 6px 10px; border-radius: var(--radius-md); font-size: 12px; font-family: var(--font-sans); cursor: pointer;
    margin-left: auto;
  }
  .cal-today:hover { background: var(--surface-hover); }

  .cal-daynames {
    display: grid; grid-template-columns: repeat(7, 1fr); flex-shrink: 0;
    border-bottom: 1px solid var(--border); background: var(--surface);
  }
  .cal-dayname {
    text-align: center; font-size: 10px; text-transform: uppercase; letter-spacing: .06em;
    color: var(--text-faint); padding: 6px 0;
  }

  .cal-grid {
    display: grid; grid-template-columns: repeat(7, 1fr); grid-auto-rows: 1fr;
    flex: 1; min-height: 0; overflow-y: auto;
  }
  .cal-cell {
    border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
    padding: 4px; min-height: 90px; display: flex; flex-direction: column; gap: 2px; min-width: 0;
  }
  .cal-empty { background: var(--surface-alt); }
  .cal-daynum { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
  .cal-today .cal-daynum { color: var(--accent); font-weight: 700; }

  .cal-entries { display: flex; flex-direction: column; gap: 2px; overflow-y: auto; min-height: 0; }
  .cal-chip {
    display: flex; align-items: center; gap: 4px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 11px; padding: 2px 4px;
    cursor: pointer; text-align: left; width: 100%; overflow: hidden;
  }
  .cal-chip:hover { background: var(--surface-hover); }
  .cal-chip.overdue { background: color-mix(in srgb, var(--danger) 15%, var(--surface-alt)); color: var(--danger); }
  .chip-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  @media (max-width: 700px) {
    .cal-cell { min-height: 60px; }
    .chip-label { display: none; }
  }
</style>
