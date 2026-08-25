import { describe, it, expect } from "vitest";
import { displayName, formatDue, earliestDue } from "../src/lib/choreFormat";
import type { Chore, Assignment } from "../src/lib/choreStore.svelte";

function makeChore(name: string, emoji: string): Chore {
  return {
    id: "c1",
    donetickId: null,
    name,
    emoji,
    periodDays: 7,
    frequencyType: "interval",
    frequency: 7,
    frequencyMetadata: {},
    scheduleFromDue: false,
    nextDueDate: new Date().toISOString(),
    description: "",
  };
}

describe("choreFormat — displayName", () => {
  it("strips a leading emoji that duplicates chore.emoji", () => {
    expect(displayName(makeChore("🧹 Sweep", "🧹"))).toBe("Sweep");
  });

  it("leaves the name untouched when it doesn't start with the emoji", () => {
    expect(displayName(makeChore("Sweep", "🧹"))).toBe("Sweep");
  });
});

describe("choreFormat — formatDue", () => {
  it("returns an em dash for an empty string", () => {
    expect(formatDue("")).toBe("—");
  });

  it("labels today, tomorrow, and overdue days", () => {
    const today = new Date();
    expect(formatDue(today.toISOString())).toBe("Today");

    const tomorrow = new Date(today.getTime() + 86400000);
    expect(formatDue(tomorrow.toISOString())).toBe("Tomorrow");

    const twoDaysAgo = new Date(today.getTime() - 2 * 86400000);
    expect(formatDue(twoDaysAgo.toISOString())).toBe("2d overdue");
  });
});

function makeAssignment(nextDueDate: string): Assignment {
  return { id: "a1", choreId: "c1", roomId: null, position: null, nextDueDate, label: null };
}

describe("choreFormat — earliestDue", () => {
  it("falls back to the chore's own nextDueDate when it has no assignments", () => {
    const chore = makeChore("Sweep", "🧹");
    chore.nextDueDate = "2026-08-07T00:00:00Z";
    expect(earliestDue(chore, [])).toBe("2026-08-07T00:00:00Z");
  });

  it("prefers the earliest assignment due date over a stale chore-level one", () => {
    // Completing a single assignment advances only that assignment's
    // nextDueDate, leaving the chore's own field stale -- the earliest
    // assignment date is the real next due, same as what the chores list shows.
    const chore = makeChore("Sweep", "🧹");
    chore.nextDueDate = "2026-08-07T00:00:00Z";
    const assignments = [makeAssignment("2026-09-14T00:00:00Z"), makeAssignment("2026-10-01T00:00:00Z")];
    expect(earliestDue(chore, assignments)).toBe("2026-09-14T00:00:00Z");
  });
});
