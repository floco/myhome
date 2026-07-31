import { getStoredLocale } from "./locale";

export type DateFormat = "MDY" | "DMY" | "ISO" | "LONG";
export type TimeFormat = "12h" | "24h";
export type WeekStart = 0 | 1 | 6;

const STORAGE_KEY = "myhome-localization";

interface LocalizationOverrides {
  dateFormat: DateFormat | null;
  timeFormat: TimeFormat | null;
  weekStart: WeekStart | null;
}

const EMPTY_OVERRIDES: LocalizationOverrides = { dateFormat: null, timeFormat: null, weekStart: null };

const LANGUAGE_DEFAULTS: Record<"en" | "fr", { dateFormat: DateFormat; timeFormat: TimeFormat; weekStart: WeekStart }> = {
  en: { dateFormat: "MDY", timeFormat: "12h", weekStart: 0 },
  fr: { dateFormat: "DMY", timeFormat: "24h", weekStart: 1 },
};

function readOverrides(): LocalizationOverrides {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return { ...EMPTY_OVERRIDES };
  try {
    const parsed = JSON.parse(raw) as Partial<LocalizationOverrides>;
    return {
      dateFormat: parsed.dateFormat ?? null,
      timeFormat: parsed.timeFormat ?? null,
      weekStart: parsed.weekStart ?? null,
    };
  } catch {
    return { ...EMPTY_OVERRIDES };
  }
}

function writeOverrides(overrides: LocalizationOverrides): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

function languageDefaults() {
  return LANGUAGE_DEFAULTS[getStoredLocale()];
}

export function getDateFormat(): DateFormat {
  return readOverrides().dateFormat ?? languageDefaults().dateFormat;
}

export function setDateFormat(format: DateFormat): void {
  writeOverrides({ ...readOverrides(), dateFormat: format });
}

export function getTimeFormat(): TimeFormat {
  return readOverrides().timeFormat ?? languageDefaults().timeFormat;
}

export function setTimeFormat(format: TimeFormat): void {
  writeOverrides({ ...readOverrides(), timeFormat: format });
}

export function getWeekStart(): WeekStart {
  return readOverrides().weekStart ?? languageDefaults().weekStart;
}

export function setWeekStart(weekStart: WeekStart): void {
  writeOverrides({ ...readOverrides(), weekStart });
}
