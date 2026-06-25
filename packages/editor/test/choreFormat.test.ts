import { describe, it, expect } from "vitest";
import { displayName, formatDue } from "../src/lib/choreFormat";
import type { Chore } from "../src/lib/choreStore.svelte";

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
