import type { Locale } from "./locale";
import { getStoredLocale } from "./locale";
import type { DateFormat, TimeFormat } from "./localization";
import { getDateFormat, getTimeFormat } from "./localization";

function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export function formatDateWithOptions(
  value: string | Date | null | undefined,
  format: DateFormat,
  loc: Locale,
): string {
  const d = toDate(value);
  if (!d) return "—";
  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  if (format === "MDY") return `${pad(month)}/${pad(day)}/${year}`;
  if (format === "DMY") return `${pad(day)}/${pad(month)}/${year}`;
  if (format === "ISO") return `${year}-${pad(month)}-${pad(day)}`;
  return new Intl.DateTimeFormat(loc, { month: "long", day: "numeric", year: "numeric" }).format(d);
}

export function formatTimeWithOptions(
  value: string | Date | null | undefined,
  timeFormat: TimeFormat,
  loc: Locale,
): string {
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat(loc, {
    hour: "numeric",
    minute: "2-digit",
    hour12: timeFormat === "12h",
  }).format(d);
}

export function formatDate(value: string | Date | null | undefined): string {
  return formatDateWithOptions(value, getDateFormat(), getStoredLocale());
}

export function formatTime(value: string | Date | null | undefined): string {
  return formatTimeWithOptions(value, getTimeFormat(), getStoredLocale());
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const d = toDate(value);
  if (!d) return "—";
  return `${formatDate(d)} ${formatTime(d)}`;
}

export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
