import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoreCalendarView from "../src/lib/components/ChoreCalendarView.svelte";
import type { Chore, Assignment } from "../src/lib/choreStore.svelte";

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1", donetickId: null, name: "🧹 Sweep kitchen", emoji: "🧹",
    periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {},
    scheduleFromDue: false, nextDueDate: "2026-08-01T12:00:00.000Z", description: "", attachments: [],
    ...overrides,
  };
}

function makeAssignment(overrides: Partial<Assignment> = {}): Assignment {
  return {
    id: "a1", choreId: "c1", roomId: null, position: null,
    nextDueDate: "2026-08-01T12:00:00.000Z", label: null,
    ...overrides,
  };
}

describe("ChoreCalendarView", () => {
  let target: HTMLDivElement;
  let currentApp: ReturnType<typeof mount>;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    unmount(currentApp);
    target.remove();
  });

  it("places a chore's chip on the grid cell matching its assignment's due date", () => {
    const chore = makeChore();
    const assignment = makeAssignment({ nextDueDate: "2026-08-15T12:00:00.000Z" });
    currentApp = mount(ChoreCalendarView, {
      target,
      props: { chores: [chore], assignments: [assignment], month: 7, year: 2026, onmonthchange: vi.fn(), onchoreclick: vi.fn() },
    });
    flushSync();

    const cells = [...target.querySelectorAll(".cal-cell")];
    const cellWithChip = cells.find((c) => c.querySelector(".cal-chip"));
    expect(cellWithChip?.querySelector(".cal-daynum")?.textContent).toBe("15");
    expect(cellWithChip?.querySelector(".cal-chip")?.textContent).toContain("Sweep kitchen");
  });

  it("calls onchoreclick with the chore id when a chip is clicked", () => {
    const chore = makeChore();
    const assignment = makeAssignment({ nextDueDate: "2026-08-15T12:00:00.000Z" });
    const onchoreclick = vi.fn();
    currentApp = mount(ChoreCalendarView, {
      target,
      props: { chores: [chore], assignments: [assignment], month: 7, year: 2026, onmonthchange: vi.fn(), onchoreclick },
    });
    flushSync();

    const chip = target.querySelector(".cal-chip") as HTMLButtonElement;
    chip.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onchoreclick).toHaveBeenCalledWith("c1");
  });

  it("marks a chip overdue when its due date has passed", () => {
    const chore = makeChore();
    const assignment = makeAssignment({ nextDueDate: "2020-01-01T00:00:00.000Z" });
    currentApp = mount(ChoreCalendarView, {
      target,
      props: { chores: [chore], assignments: [assignment], month: 0, year: 2020, onmonthchange: vi.fn(), onchoreclick: vi.fn() },
    });
    flushSync();

    expect(target.querySelector(".cal-chip")?.classList.contains("overdue")).toBe(true);
  });

  it("excludes assignments for a different room when roomFilter is set", () => {
    const chore = makeChore();
    const assignment = makeAssignment({ id: "a1", roomId: "kitchen", nextDueDate: "2026-08-15T12:00:00.000Z" });
    currentApp = mount(ChoreCalendarView, {
      target,
      props: {
        chores: [chore], assignments: [assignment], month: 7, year: 2026,
        roomFilter: "bathroom", onmonthchange: vi.fn(), onchoreclick: vi.fn(),
      },
    });
    flushSync();

    expect(target.querySelector(".cal-chip")).toBeNull();
  });

  it("calls onmonthchange with the previous month when the prev button is clicked", () => {
    const onmonthchange = vi.fn();
    currentApp = mount(ChoreCalendarView, {
      target,
      props: { chores: [], assignments: [], month: 0, year: 2026, onmonthchange, onchoreclick: vi.fn() },
    });
    flushSync();

    (target.querySelector(".cal-prev") as HTMLButtonElement).click();
    flushSync();

    expect(onmonthchange).toHaveBeenCalledWith(2025, 11);
  });

  it("calls onmonthchange with the next month when the next button is clicked", () => {
    const onmonthchange = vi.fn();
    currentApp = mount(ChoreCalendarView, {
      target,
      props: { chores: [], assignments: [], month: 11, year: 2026, onmonthchange, onchoreclick: vi.fn() },
    });
    flushSync();

    (target.querySelector(".cal-next") as HTMLButtonElement).click();
    flushSync();

    expect(onmonthchange).toHaveBeenCalledWith(2027, 0);
  });

  it("renders 7 day-of-week headers starting from the locale's week start", () => {
    currentApp = mount(ChoreCalendarView, {
      target,
      props: { chores: [], assignments: [], month: 0, year: 2026, onmonthchange: vi.fn(), onchoreclick: vi.fn() },
    });
    flushSync();

    const headers = [...target.querySelectorAll(".cal-dayname")].map((h) => h.textContent);
    expect(headers).toHaveLength(7);
    expect(headers[0]).toBe("Sun");
  });
});
