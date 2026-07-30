import { describe, expect, it } from "vitest";
import { locale } from "svelte-i18n";
import { get } from "svelte/store";
import { scheduleLabel, type Chore } from "./choreStore.svelte";

function makeChore(overrides: Partial<Chore>): Chore {
  return {
    id: "c1",
    donetickId: null,
    name: "Test",
    emoji: "🧹",
    periodDays: 365,
    frequencyType: "yearly",
    frequency: 1,
    frequencyMetadata: {},
    scheduleFromDue: false,
    nextDueDate: "2026-01-01",
    description: "",
    attachments: [],
    ...overrides,
  };
}

describe("scheduleLabel", () => {
  it("ignores a stray non-1 frequency value on a literal yearly chore", () => {
    // Donetick's own scheduler advances "yearly" chores by exactly 1 year and
    // ignores `frequency` entirely for that literal type -- a chore imported
    // with frequency: 3 still recurs yearly, not every 3 years.
    const chore = makeChore({ frequencyType: "yearly", frequency: 3 });
    expect(scheduleLabel(chore)).toBe("Yearly");
  });

  it("ignores a stray non-1 frequency value on a literal monthly chore", () => {
    const chore = makeChore({ frequencyType: "monthly", frequency: 2 });
    expect(scheduleLabel(chore)).toBe("Monthly");
  });

  it("ignores a stray non-1 frequency value on a literal weekly chore", () => {
    const chore = makeChore({ frequencyType: "weekly", frequency: 5 });
    expect(scheduleLabel(chore)).toBe("Weekly");
  });

  it("still multiplies for the interval type", () => {
    const chore = makeChore({ frequencyType: "interval", frequency: 3, frequencyMetadata: { unit: "years" } });
    expect(scheduleLabel(chore)).toBe("Every 3 years");
  });

  it("renders yearly correctly in French too", async () => {
    locale.set("fr");
    const chore = makeChore({ frequencyType: "yearly", frequency: 3 });
    expect(scheduleLabel(chore)).toBe("Annuel");
    locale.set("en");
  });
});
