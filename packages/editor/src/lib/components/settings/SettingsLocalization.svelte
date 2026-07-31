<!-- packages/editor/src/lib/components/settings/SettingsLocalization.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Card from "../ui/Card.svelte";
  import { getStoredLocale, setLocale, type Locale } from "../../locale";
  import {
    getDateFormat, setDateFormat, type DateFormat,
    getTimeFormat, setTimeFormat, type TimeFormat,
    getWeekStart, setWeekStart, type WeekStart,
  } from "../../localization";
  import { formatDateWithOptions, formatTimeWithOptions } from "../../dateFormat";

  let currentLocale = $state<Locale>(getStoredLocale());
  let currentDateFormat = $state<DateFormat>(getDateFormat());
  let currentTimeFormat = $state<TimeFormat>(getTimeFormat());
  let currentWeekStart = $state<WeekStart>(getWeekStart());

  const PREVIEW_DATE = new Date(2024, 0, 15, 14, 30);

  function changeLocale(next: Locale): void {
    currentLocale = next;
    setLocale(next);
  }

  function changeDateFormat(next: DateFormat): void {
    currentDateFormat = next;
    setDateFormat(next);
  }

  function changeTimeFormat(next: TimeFormat): void {
    currentTimeFormat = next;
    setTimeFormat(next);
  }

  function changeWeekStart(next: WeekStart): void {
    currentWeekStart = next;
    setWeekStart(next);
  }

  const datePreview = $derived(formatDateWithOptions(PREVIEW_DATE, currentDateFormat, currentLocale));
  const timePreview = $derived(formatTimeWithOptions(PREVIEW_DATE, currentTimeFormat, currentLocale));
</script>

<Card>
  <div class="section-header">
    <h2>{$_('settings.nav.localization')}</h2>
  </div>
  <p class="section-desc">{$_('settings.localization.description')}</p>

  <div class="loc-field">
    <label class="loc-label" for="loc-language">{$_('settings.localization.language')}</label>
    <p class="loc-field-desc">{$_('settings.localization.languageDescription')}</p>
    <select
      id="loc-language"
      class="loc-select lang-select"
      value={currentLocale}
      onchange={(e) => changeLocale((e.target as HTMLSelectElement).value as Locale)}
    >
      <option value="en">English</option>
      <option value="fr">Français</option>
    </select>
  </div>

  <div class="loc-field">
    <label class="loc-label" for="loc-date-format">{$_('settings.localization.dateFormat')}</label>
    <p class="loc-field-desc">{$_('settings.localization.dateFormatDescription')}</p>
    <select
      id="loc-date-format"
      class="loc-select dateformat-select"
      value={currentDateFormat}
      onchange={(e) => changeDateFormat((e.target as HTMLSelectElement).value as DateFormat)}
    >
      <option value="MDY">MM/DD/YYYY</option>
      <option value="DMY">DD/MM/YYYY</option>
      <option value="ISO">YYYY-MM-DD</option>
      <option value="LONG">Month DD, YYYY</option>
    </select>
    <p class="loc-preview">{$_('settings.localization.preview', { values: { value: datePreview } })}</p>
  </div>

  <div class="loc-field">
    <label class="loc-label" for="loc-time-format">{$_('settings.localization.timeFormat')}</label>
    <p class="loc-field-desc">{$_('settings.localization.timeFormatDescription')}</p>
    <select
      id="loc-time-format"
      class="loc-select timeformat-select"
      value={currentTimeFormat}
      onchange={(e) => changeTimeFormat((e.target as HTMLSelectElement).value as TimeFormat)}
    >
      <option value="12h">{$_('settings.localization.time12')}</option>
      <option value="24h">{$_('settings.localization.time24')}</option>
    </select>
    <p class="loc-preview">{$_('settings.localization.preview', { values: { value: timePreview } })}</p>
  </div>

  <div class="loc-field">
    <label class="loc-label" for="loc-week-start">{$_('settings.localization.firstDayOfWeek')}</label>
    <p class="loc-field-desc">{$_('settings.localization.firstDayOfWeekDescription')}</p>
    <select
      id="loc-week-start"
      class="loc-select weekstart-select"
      value={currentWeekStart}
      onchange={(e) => changeWeekStart(parseInt((e.target as HTMLSelectElement).value, 10) as WeekStart)}
    >
      <option value={0}>{$_('settings.localization.weekday.sunday')}</option>
      <option value={1}>{$_('settings.localization.weekday.monday')}</option>
      <option value={6}>{$_('settings.localization.weekday.saturday')}</option>
    </select>
  </div>
</Card>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 16px; }
  .loc-field { padding: 10px 0; border-top: 1px solid var(--border); }
  .loc-field:first-of-type { border-top: none; }
  .loc-label { display: block; font-size: 13px; font-weight: 500; color: var(--text); margin-bottom: 2px; }
  .loc-field-desc { font-size: 12px; color: var(--text-muted); margin: 0 0 8px; }
  .loc-select { font-size: 13px; padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--surface); color: var(--text); }
  .loc-preview { font-size: 12px; color: var(--text-muted); margin: 6px 0 0; }
</style>
