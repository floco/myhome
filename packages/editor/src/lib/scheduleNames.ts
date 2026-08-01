// Donetick stores weekdays/months as full English name strings (e.g.
// "Monday", "March"), compared case-insensitively -- never ints. These
// converters normalize either shape to the 1-based int myhome's own UI and
// scheduler use (Mon=1..Sun=7, Jan=1..Dec=12).

const WEEKDAY_NUMS: Record<string, number> = {
  monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6, sunday: 7,
  mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6, sun: 7,
};

const MONTH_NUMS: Record<string, number> = {
  january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
  july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
  jan: 1, feb: 2, mar: 3, apr: 4, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12,
};

function toNum(v: unknown, names: Record<string, number>): number | null {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const named = names[v.toLowerCase().trim()];
    if (named !== undefined) return named;
    const parsed = Number(v);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function toWeekdayNum(v: unknown): number | null {
  return toNum(v, WEEKDAY_NUMS);
}

export function toMonthNum(v: unknown): number | null {
  return toNum(v, MONTH_NUMS);
}
