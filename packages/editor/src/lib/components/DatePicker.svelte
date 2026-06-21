<!-- packages/editor/src/lib/components/DatePicker.svelte -->
<script lang="ts">
  interface Props {
    value?: string;
    placeholder?: string;
  }
  let { value = $bindable(""), placeholder = "Pick a date…" }: Props = $props();

  let open = $state(false);
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());

  const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const DAY_HEADERS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

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
    <span class="dp-text">{displayValue() || placeholder}</span>
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
    background: #0f0f24; border: 1px solid #2a2a4a; color: #ccc;
    padding: 5px 8px; border-radius: 4px; cursor: pointer;
    font-size: 12px; font-family: sans-serif; min-width: 160px;
    user-select: none;
  }
  .dp-field:hover { border-color: #5566cc; }
  .dp-text { flex: 1; }
  .dp-icon { font-size: 13px; flex-shrink: 0; }

  .dp-calendar {
    position: absolute; top: calc(100% + 4px); left: 0;
    background: #1a1a30; border: 1px solid #3a3a5a; border-radius: 8px;
    padding: 10px; z-index: 300; box-shadow: 0 4px 16px #0008;
    min-width: 220px;
  }

  .dp-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 8px;
  }
  .dp-nav {
    background: none; border: none; color: #88a; font-size: 16px;
    cursor: pointer; padding: 0 6px; line-height: 1;
  }
  .dp-nav:hover { color: #aaf; }
  .dp-month-label { font-size: 12px; color: #ccc; font-family: sans-serif; font-weight: 600; }

  .dp-grid {
    display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;
  }
  .dp-dh {
    text-align: center; font-size: 9px; color: #445; padding: 2px 0;
    font-family: sans-serif;
  }
  .dp-cell {
    text-align: center; font-size: 11px; font-family: sans-serif;
    padding: 4px 2px; border-radius: 3px; cursor: pointer;
    background: none; border: none; color: #aaa;
  }
  .dp-cell:hover:not(.dp-selected) { background: #2a2a4a; color: #eee; }
  .dp-empty { cursor: default; }
  .dp-today { color: #88aaff; font-weight: 600; }
  .dp-selected { background: #3344aa; color: #fff; font-weight: 600; }
  .dp-selected:hover { background: #4455cc; }
</style>
