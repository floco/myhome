export interface ParsedSchedule {
  name: string;
  schedule: {
    frequencyType: string;
    frequency: number;
    frequencyMetadata: Record<string, unknown>;
  };
}

const WEEKDAY_NUM: Record<string, number> = {
  monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6, sunday: 7,
  lundi: 1, mardi: 2, mercredi: 3, jeudi: 4, vendredi: 5, samedi: 6, dimanche: 7,
};

const ORDINAL_NUM: Record<string, number> = {
  "1st": 1, first: 1, "1er": 1, premier: 1, première: 1, premiere: 1,
  "2nd": 2, second: 2, seconde: 2, "2e": 2, deuxième: 2, deuxieme: 2,
  "3rd": 3, third: 3, "3e": 3, troisième: 3, troisieme: 3,
  "4th": 4, fourth: 4, "4e": 4, quatrième: 4, quatrieme: 4,
  last: -1, dernier: -1, dernière: -1, derniere: -1,
};

const UNIT_WORDS: Record<string, "days" | "weeks" | "months" | "years"> = {
  day: "days", days: "days", jour: "days", jours: "days",
  week: "weeks", weeks: "weeks", semaine: "weeks", semaines: "weeks",
  month: "months", months: "months", mois: "months",
  year: "years", years: "years", an: "years", ans: "years",
  année: "years", annee: "years", années: "years", annees: "years",
};

function normalizeDayToken(token: string): number | null {
  const clean = token.trim().toLowerCase().replace(/s$/, "");
  return WEEKDAY_NUM[clean] ?? null;
}

function stripMatch(text: string, match: RegExpMatchArray): string {
  const idx = match.index ?? 0;
  const before = text.slice(0, idx);
  const after = text.slice(idx + match[0].length);
  const cleaned = (before + " " + after).replace(/\s+/g, " ").trim().replace(/[,.;:]+$/, "");
  return cleaned.length > 0 ? cleaned : text.trim();
}

export function parseScheduleText(text: string, loc: "en" | "fr"): ParsedSchedule | null {
  const trimmed = text.trim();
  if (!trimmed) return null;

  const dailyRe = loc === "fr" ? /\btous\s+les\s+jours\b|\bquotidien(?:nement)?\b/i : /\bevery\s+day\b|\bdaily\b/i;
  const dailyMatch = trimmed.match(dailyRe);
  if (dailyMatch) {
    return { name: stripMatch(trimmed, dailyMatch), schedule: { frequencyType: "daily", frequency: 1, frequencyMetadata: {} } };
  }

  const yearlyRe = loc === "fr"
    ? /\bchaque\s+ann[ée]e\b|\btous\s+les\s+ans\b|\bannuellement\b/i
    : /\bevery\s+year\b|\byearly\b|\bannually\b/i;
  const yearlyMatch = trimmed.match(yearlyRe);
  if (yearlyMatch) {
    return { name: stripMatch(trimmed, yearlyMatch), schedule: { frequencyType: "yearly", frequency: 1, frequencyMetadata: {} } };
  }

  const dayNames = loc === "fr"
    ? "lundis?|mardis?|mercredis?|jeudis?|vendredis?|samedis?|dimanches?"
    : "mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?";
  const dayListRe = `(?:${dayNames})(?:\\s*(?:,|${loc === "fr" ? "et" : "and"})\\s*(?:${dayNames}))*`;
  const weekdayRe = loc === "fr"
    ? new RegExp(`\\b(?:tous\\s+les|chaque)\\s+(${dayListRe})`, "i")
    : new RegExp(`\\b(?:every|each)\\s+(${dayListRe})`, "i");
  const weekdayMatch = trimmed.match(weekdayRe);
  if (weekdayMatch) {
    const splitRe = loc === "fr" ? /,|et/i : /,|and/i;
    const days = weekdayMatch[1]
      .split(splitRe)
      .map((t) => normalizeDayToken(t))
      .filter((n): n is number => n !== null)
      .sort((a, b) => a - b);
    if (days.length > 0) {
      return { name: stripMatch(trimmed, weekdayMatch), schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days } } };
    }
  }

  const ordinalWords = Object.keys(ORDINAL_NUM).join("|");
  const periodWords = loc === "fr" ? "mois|trimestre" : "month|quarter";
  const nthWeekdayRe = loc === "fr"
    ? new RegExp(`\\ble\\s+(${ordinalWords})\\s+(${dayNames})\\s+(?:du|de\\s+chaque)\\s+(${periodWords})\\b`, "i")
    : new RegExp(`\\b(?:every|the)\\s+(${ordinalWords})\\s+(${dayNames})\\s+of\\s+(?:the|every)\\s+(${periodWords})\\b`, "i");
  const nthWeekdayMatch = trimmed.match(nthWeekdayRe);
  if (nthWeekdayMatch) {
    const occurrence = ORDINAL_NUM[nthWeekdayMatch[1].toLowerCase()];
    const day = normalizeDayToken(nthWeekdayMatch[2]);
    const periodWord = nthWeekdayMatch[3].toLowerCase();
    const weekPattern = periodWord === "month" || periodWord === "mois" ? "week_of_month" : "week_of_quarter";
    if (occurrence !== undefined && day !== null) {
      return {
        name: stripMatch(trimmed, nthWeekdayMatch),
        schedule: { frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [day], weekPattern, occurrences: [occurrence] } },
      };
    }
  }

  const domRe = loc === "fr"
    ? /\ble\s+(\d{1,2})(?:er)?\s+de\s+chaque\s+mois\b/i
    : /\bon\s+the\s+(\d{1,2})(?:st|nd|rd|th)?\s+of\s+every\s+month\b/i;
  const domMatch = trimmed.match(domRe);
  if (domMatch) {
    const day = Math.min(31, Math.max(1, parseInt(domMatch[1], 10)));
    return { name: stripMatch(trimmed, domMatch), schedule: { frequencyType: "day_of_the_month", frequency: day, frequencyMetadata: {} } };
  }

  const unitWords = Object.keys(UNIT_WORDS).join("|");
  const intervalRe = loc === "fr"
    ? new RegExp(`\\btous\\s+les\\s+(\\d+)\\s+(${unitWords})\\b`, "i")
    : new RegExp(`\\bevery\\s+(\\d+)\\s+(${unitWords})\\b`, "i");
  const intervalMatch = trimmed.match(intervalRe);
  if (intervalMatch) {
    const n = Math.max(1, parseInt(intervalMatch[1], 10));
    const unit = UNIT_WORDS[intervalMatch[2].toLowerCase()] ?? "days";
    return { name: stripMatch(trimmed, intervalMatch), schedule: { frequencyType: "interval", frequency: n, frequencyMetadata: { unit } } };
  }

  const bareRe = loc === "fr" ? /\btous\s+les\s+(\d+)\b/i : /\bevery\s+(\d+)\b/i;
  const bareMatch = trimmed.match(bareRe);
  if (bareMatch) {
    const n = Math.max(1, parseInt(bareMatch[1], 10));
    return { name: stripMatch(trimmed, bareMatch), schedule: { frequencyType: "interval", frequency: n, frequencyMetadata: { unit: "days" } } };
  }

  return null;
}
