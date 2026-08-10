import { describe, it, expect, afterEach, vi } from "vitest";
import { locale } from "svelte-i18n";
import { createChoreStore, scheduleLabel, type Chore } from "../src/lib/choreStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const emptyDoc = { version: 1, chores: [], assignments: [] };

const sampleDoc = {
  version: 1,
  chores: [
    { id: "c1", donetickId: null, name: "🧹 Sweep", emoji: "🧹", periodDays: 14, nextDueDate: new Date(Date.now() + 7 * 86400000).toISOString(), description: "" },
    { id: "c2", donetickId: null, name: "🪟 Windows", emoji: "🪟", periodDays: 365, nextDueDate: new Date(Date.now() - 5 * 86400000).toISOString(), description: "" },
  ],
  assignments: [
    { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 2 } },
    { id: "a2", choreId: "c2", roomId: null, position: null },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("choreStore — init", () => {
  it("starts empty and loads from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    expect(store.chores.length).toBe(2);
    expect(store.assignments.length).toBe(2);
    expect(store.loaded).toBe(true);
  });

  it("marks loaded even on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));
    const store = createChoreStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network error");
  });

  it("returns empty arrays when API returns empty doc", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    expect(store.chores).toEqual([]);
    expect(store.assignments).toEqual([]);
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createChoreStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("choreStore — getProgress", () => {
  it("returns ~0.5 when half period remains", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    const halfRemaining = new Date(Date.now() + 7 * 86400000).toISOString();
    const assignment = { id: "a1", choreId: "x", roomId: null, position: null, nextDueDate: halfRemaining, label: null };
    const pct = store.getProgress(assignment, { id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: halfRemaining, description: "" });
    expect(pct).toBeCloseTo(0.5, 1);
  });

  it("returns 0 when overdue", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    const overdue = new Date(Date.now() - 86400000).toISOString();
    const assignment = { id: "a1", choreId: "x", roomId: null, position: null, nextDueDate: overdue, label: null };
    const pct = store.getProgress(assignment, { id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: overdue, description: "" });
    expect(pct).toBe(0);
  });

  it("returns 1 when just scheduled", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    const fullRemaining = new Date(Date.now() + 14 * 86400000).toISOString();
    const assignment = { id: "a1", choreId: "x", roomId: null, position: null, nextDueDate: fullRemaining, label: null };
    const pct = store.getProgress(assignment, { id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: fullRemaining, description: "" });
    expect(pct).toBeCloseTo(1, 1);
  });
});

describe("choreStore — getColor", () => {
  it("returns green for >50%", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    expect(store.getColor(0.8)).toBe("#4caf50");
  });

  it("returns orange for 25-50%", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    expect(store.getColor(0.4)).toBe("#ff9800");
  });

  it("returns red for <25% or overdue", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    expect(store.getColor(0.1)).toBe("#f44336");
    expect(store.getColor(0)).toBe("#f44336");
  });
});

describe("choreStore — assignmentsForRoom", () => {
  it("returns only assignments for the specified room", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    const forR1 = store.assignmentsForRoom("r1");
    expect(forR1.length).toBe(1);
    expect(forR1[0].id).toBe("a1");
  });

  it("returns empty array for unknown room", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    expect(store.assignmentsForRoom("unknown")).toEqual([]);
  });

  it("does not include house-level assignments", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore(getHomeId);
    await tick();
    const forR1 = store.assignmentsForRoom("r1");
    expect(forR1.every((a) => a.roomId !== null)).toBe(true);
  });
});

describe("choreStore — importFromDonetick", () => {
  function makeImportFetch(status: number, body: unknown) {
    return vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/chores/import")) {
        return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => emptyDoc });
    });
  }

  it("throws the backend's detail message on failure", async () => {
    vi.stubGlobal("fetch", makeImportFetch(502, { detail: "Donetick error: [Errno -2] Name or service not known" }));
    const store = createChoreStore(getHomeId);
    await tick();
    await expect(store.importFromDonetick("token", "https://bad.example.com")).rejects.toThrow(
      "Donetick error: [Errno -2] Name or service not known",
    );
  });

  it("falls back to a status code message when the body has no detail", async () => {
    vi.stubGlobal("fetch", makeImportFetch(502, {}));
    const store = createChoreStore(getHomeId);
    await tick();
    await expect(store.importFromDonetick("token", "https://bad.example.com")).rejects.toThrow("HTTP 502");
  });
});

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

  it("renders a literal daily chore as 'Daily', not a raw periodDays fallback", () => {
    // Caught by manual browser testing: a chore created via the new "Daily"
    // recurrence category (frequencyType: "daily") fell through to the
    // generic `${periodDays}d` fallback since there was no explicit branch
    // for it here (chore_scheduling.py and scheduleCategory both already had
    // one; this file was the one place that got missed).
    const chore = makeChore({ frequencyType: "daily", frequency: 1, frequencyMetadata: {}, periodDays: 1 });
    expect(scheduleLabel(chore)).toBe("Daily");
  });

  it("renders yearly correctly in French too", async () => {
    locale.set("fr");
    const chore = makeChore({ frequencyType: "yearly", frequency: 3 });
    expect(scheduleLabel(chore)).toBe("Annuel");
    locale.set("en");
  });

  it("shows the current period for an adaptive chore", () => {
    const chore = makeChore({ frequencyType: "adaptive", frequency: 1, frequencyMetadata: {}, periodDays: 42 });
    expect(scheduleLabel(chore)).toBe("Adaptive (~42 days)");
  });

  it("renders a plain days_of_the_week label from Donetick-shaped string day names", () => {
    // Donetick stores `days` as full English day-name strings (e.g. "Monday"),
    // not ints -- (`"Monday" - 1`) is NaN in JS, so this silently broke before
    // the shared toWeekdayNum normalizer was wired in here.
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: ["Monday", "Wednesday"] } });
    expect(scheduleLabel(chore)).toBe("Weekly on Mon, Wed");
  });

  it("renders a 2nd-Tuesday-of-the-month schedule", () => {
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [2], weekPattern: "week_of_month", occurrences: [2] } });
    expect(scheduleLabel(chore)).toBe("2nd Tue of the month");
  });

  it("renders a last-Friday-of-the-quarter schedule", () => {
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [5], weekPattern: "week_of_quarter", occurrences: [-1] } });
    expect(scheduleLabel(chore)).toBe("Last Fri of the quarter");
  });

  it("renders a Donetick-imported Nth-weekday schedule with a string day name", () => {
    const chore = makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: ["Tuesday"], weekPattern: "week_of_month", occurrences: [2] } });
    expect(scheduleLabel(chore)).toBe("2nd Tue of the month");
  });

  it("shows month names instead of 'Monthly' when day_of_the_month is restricted to specific months", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 20, frequencyMetadata: { months: [8] } });
    expect(scheduleLabel(chore)).toBe("On day 20 (Aug)");
  });

  it("joins multiple restricted months in calendar order regardless of input order", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 15, frequencyMetadata: { months: [10, 1, 4, 7] } });
    expect(scheduleLabel(chore)).toBe("On day 15 (Jan, Apr, Jul, Oct)");
  });

  it("keeps the plain 'Monthly on day N' label when no months restriction is set", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 20, frequencyMetadata: {} });
    expect(scheduleLabel(chore)).toBe("Monthly on day 20");
  });

  it("handles Donetick-shaped string month names in the restriction", () => {
    const chore = makeChore({ frequencyType: "day_of_the_month", frequency: 15, frequencyMetadata: { months: ["March", "June", "September", "December"] } });
    expect(scheduleLabel(chore)).toBe("On day 15 (Mar, Jun, Sep, Dec)");
  });
});

describe("choreStore — completedOn", () => {
  it("completeChore omits completedOn from the request body when not provided", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.completeChore("c1", "done");

    const completeCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/complete"));
    expect(completeCall).toBeDefined();
    const sentBody = JSON.parse(completeCall![1].body as string);
    expect(sentBody).toEqual({ notes: "done" });
  });

  it("completeChore includes completedOn in the request body when provided", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.completeChore("c1", "done", "2026-07-01");

    const completeCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/complete"));
    const sentBody = JSON.parse(completeCall![1].body as string);
    expect(sentBody).toEqual({ notes: "done", completedOn: "2026-07-01" });
  });

  it("completeAssignment includes completedOn in the request body when provided", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.completeAssignment("a1", "", "2026-07-01");

    const completeCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/complete"));
    const sentBody = JSON.parse(completeCall![1].body as string);
    expect(sentBody).toEqual({ notes: "", completedOn: "2026-07-01" });
  });
});

describe("choreStore — updateAssignmentLabel", () => {
  it("PUTs the label to the assignment endpoint", async () => {
    const fetchMock = makeFetch(200, emptyDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createChoreStore(getHomeId);
    await tick();

    await store.updateAssignmentLabel("a1", "Balcony plants");

    const putCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/assignments/a1"));
    expect(putCall).toBeDefined();
    expect(putCall![1].method).toBe("PUT");
    const sentBody = JSON.parse(putCall![1].body as string);
    expect(sentBody).toEqual({ label: "Balcony plants" });
  });
});
