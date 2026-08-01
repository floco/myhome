<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import { toWeekdayNum, toMonthNum } from "../scheduleNames";

  type Category = "interval" | "daily" | "days_of_the_week" | "day_of_the_month" | "yearly" | "adaptive";

  interface Props {
    frequencyType: string;
    frequency: number;
    frequencyMetadata: Record<string, unknown>;
    periodDays: number;
    valid?: boolean;
  }

  let {
    frequencyType = $bindable(),
    frequency = $bindable(),
    frequencyMetadata = $bindable(),
    periodDays = $bindable(),
    valid = $bindable(true),
  }: Props = $props();

  const UNIT_DAYS: Record<string, number> = { days: 1, weeks: 7, months: 30, years: 365 };
  const DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

  function categoryFor(ft: string): Category {
    if (ft === "days_of_the_week") return "days_of_the_week";
    if (ft === "day_of_the_month") return "day_of_the_month";
    if (ft === "yearly") return "yearly";
    if (ft === "adaptive") return "adaptive";
    if (ft === "daily") return "daily";
    return "interval";
  }

  const initialDays = ((frequencyMetadata?.days as unknown[] | undefined) ?? [])
    .map(toWeekdayNum)
    .filter((n): n is number => n !== null);
  const initialMonths = ((frequencyMetadata?.months as unknown[] | undefined) ?? [])
    .map(toMonthNum)
    .filter((n): n is number => n !== null);

  let cat = $state<Category>(categoryFor(frequencyType));
  let intervalN = $state(frequencyType === "interval" ? frequency : 30);
  let intervalUnit = $state<"days" | "weeks" | "months" | "years">(
    (frequencyMetadata?.unit as "days" | "weeks" | "months" | "years" | undefined) ?? "days"
  );
  let selectedDays = $state<number[]>(frequencyType === "days_of_the_week" ? initialDays : []);
  let dayOfMonth = $state(frequencyType === "day_of_the_month" ? frequency : 1);
  let restrictMonths = $state(frequencyType === "day_of_the_month" && initialMonths.length > 0);
  let selectedMonths = $state<number[]>(frequencyType === "day_of_the_month" ? initialMonths : []);
  let adaptivePeriod = $state(frequencyType === "adaptive" ? periodDays : 30);

  function monthNames(loc: string): string[] {
    return Array.from({ length: 12 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { month: "long" }).format(new Date(2000, i, 1))
    );
  }
  const MONTH_NAMES = $derived(monthNames($locale ?? "en"));

  function toggleDay(d: number): void {
    selectedDays = selectedDays.includes(d) ? selectedDays.filter((x) => x !== d) : [...selectedDays, d].sort((a, b) => a - b);
  }
  function toggleMonth(m: number): void {
    selectedMonths = selectedMonths.includes(m) ? selectedMonths.filter((x) => x !== m) : [...selectedMonths, m].sort((a, b) => a - b);
  }

  $effect(() => {
    if (cat === "interval") {
      frequencyType = "interval";
      frequency = intervalN;
      frequencyMetadata = { unit: intervalUnit };
      periodDays = intervalN * UNIT_DAYS[intervalUnit];
      valid = intervalN >= 1;
    } else if (cat === "daily") {
      frequencyType = "daily";
      frequency = 1;
      frequencyMetadata = {};
      periodDays = 1;
      valid = true;
    } else if (cat === "days_of_the_week") {
      frequencyType = "days_of_the_week";
      frequency = 1;
      frequencyMetadata = { days: selectedDays };
      periodDays = 7;
      valid = selectedDays.length > 0;
    } else if (cat === "day_of_the_month") {
      frequencyType = "day_of_the_month";
      frequency = dayOfMonth;
      frequencyMetadata = restrictMonths && selectedMonths.length > 0 ? { months: selectedMonths } : {};
      periodDays = 30;
      valid = dayOfMonth >= 1 && dayOfMonth <= 31;
    } else if (cat === "yearly") {
      frequencyType = "yearly";
      frequency = 1;
      frequencyMetadata = {};
      periodDays = 365;
      valid = true;
    } else {
      frequencyType = "adaptive";
      frequency = 1;
      frequencyMetadata = {};
      periodDays = adaptivePeriod;
      valid = adaptivePeriod >= 1;
    }
  });
</script>

<div class="schedule-editor">
  <div class="field">
    <label for="se-category">{$_('chores.scheduleEditor.category')}</label>
    <select id="se-category" class="native-input" bind:value={cat}>
      <option value="interval">{$_('chores.scheduleEditor.categoryInterval')}</option>
      <option value="daily">{$_('chores.scheduleEditor.categoryDaily')}</option>
      <option value="days_of_the_week">{$_('chores.scheduleEditor.categoryWeekly')}</option>
      <option value="day_of_the_month">{$_('chores.scheduleEditor.categoryMonthly')}</option>
      <option value="yearly">{$_('chores.scheduleEditor.categoryYearly')}</option>
      <option value="adaptive">{$_('chores.scheduleEditor.categoryAdaptive')}</option>
    </select>
  </div>

  {#if cat === "interval"}
    <div class="field freq-row">
      <input type="number" class="native-input freq-n" bind:value={intervalN} min="1" />
      <select class="native-input" bind:value={intervalUnit}>
        <option value="days">{$_('chores.newModal.unitDays')}</option>
        <option value="weeks">{$_('chores.newModal.unitWeeks')}</option>
        <option value="months">{$_('chores.newModal.unitMonths')}</option>
        <option value="years">{$_('chores.newModal.unitYears')}</option>
      </select>
    </div>
  {:else if cat === "days_of_the_week"}
    <div class="field">
      <div class="day-toggles">
        {#each DAY_KEYS as key, i (key)}
          <button
            type="button"
            class="day-toggle"
            class:active={selectedDays.includes(i + 1)}
            onclick={() => toggleDay(i + 1)}
          >{$_(`chores.schedule.dayAbbrev.${key}`)}</button>
        {/each}
      </div>
      {#if selectedDays.length === 0}<div class="hint-error">{$_('chores.scheduleEditor.selectAtLeastOneDay')}</div>{/if}
    </div>
  {:else if cat === "day_of_the_month"}
    <div class="field">
      <label for="se-dom">{$_('chores.scheduleEditor.dayOfMonth')}</label>
      <input id="se-dom" type="number" class="native-input freq-n" bind:value={dayOfMonth} min="1" max="31" />
    </div>
    <div class="field-row">
      <input type="checkbox" id="se-restrict" bind:checked={restrictMonths} />
      <label for="se-restrict" class="checkbox-label">{$_('chores.scheduleEditor.restrictMonths')}</label>
    </div>
    {#if restrictMonths}
      <div class="month-toggles">
        {#each MONTH_NAMES as name, i (name)}
          <button
            type="button"
            class="day-toggle"
            class:active={selectedMonths.includes(i + 1)}
            onclick={() => toggleMonth(i + 1)}
          >{name}</button>
        {/each}
      </div>
    {/if}
  {:else if cat === "adaptive"}
    <div class="field">
      <label for="se-adaptive">{$_('chores.scheduleEditor.periodDays')}</label>
      <input id="se-adaptive" type="number" class="native-input freq-n" bind:value={adaptivePeriod} min="1" />
      <span class="hint">{$_('chores.scheduleEditor.periodDaysHint')}</span>
    </div>
  {/if}
</div>

<style>
  .schedule-editor { display: flex; flex-direction: column; gap: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field label { font-size: 11px; color: var(--text-muted); }
  .field-row { display: flex; align-items: center; gap: 8px; }
  .checkbox-label { font-size: 12px; color: var(--text-muted); cursor: pointer; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md);
    font-size: 13px; font-family: var(--font-sans); width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .freq-row { flex-direction: row; gap: 8px; }
  .freq-n { width: 80px; }
  .freq-row select { flex: 1; }
  .day-toggles, .month-toggles { display: flex; flex-wrap: wrap; gap: 6px; }
  .day-toggle {
    padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 12px; cursor: pointer;
  }
  .day-toggle.active { background: var(--accent); color: var(--accent-contrast); }
  .hint { font-size: 11px; color: var(--text-faint); }
  .hint-error { font-size: 11px; color: var(--danger); }
</style>
