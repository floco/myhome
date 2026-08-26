import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoresPage from "../src/lib/components/ChoresPage.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";
import { choreFilterState } from "../src/lib/choreFilterState.svelte";

afterEach(() => {
  document.body.innerHTML = "";
  choreFilterState.dueFilter = "attention"; // module-level state -- reset so it doesn't leak between tests
});

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1", donetickId: null, name: "Sweep kitchen", emoji: "🧹",
    periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {},
    scheduleFromDue: false, nextDueDate: "2026-08-01T12:00:00.000Z", description: "", attachments: [],
    ...overrides,
  };
}

function makeStore(chores: Chore[]) {
  return {
    chores,
    assignments: [],
    completions: [],
    loaded: true,
    loadError: null,
    createChore: vi.fn(),
    updateChore: vi.fn(),
    deleteChore: vi.fn(),
    completeChore: vi.fn(),
    delayChore: vi.fn(),
    createAssignment: vi.fn(),
    updateAssignmentPosition: vi.fn(),
    updateAssignmentLabel: vi.fn(),
    removeAssignment: vi.fn(),
    deleteAssignment: vi.fn(),
    delayAssignment: vi.fn(),
    completeAssignment: vi.fn(),
    getCompletionsForChore: vi.fn().mockReturnValue([]),
    deleteCompletion: vi.fn(),
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
    getProgress: vi.fn((assignment: { nextDueDate: string }, chore: Chore) => {
      const now = Date.now();
      const due = new Date(assignment.nextDueDate).getTime();
      const periodMs = chore.periodDays * 86400 * 1000;
      return Math.max(0, Math.min(1, (due - now) / periodMs));
    }),
    getColor: vi.fn((pct: number) => (pct > 0.5 ? "#4caf50" : pct > 0.25 ? "#ff9800" : "#f44336")),
  };
}

describe("ChoresPage — external selection", () => {
  it("opens the edit modal for the chore matching selectedItemId and clears selection", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const onclearselection = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ChoresPage, {
      target,
      props: { store, floorStore: { floors: [] }, selectedItemId: "c1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("🧹 Sweep kitchen");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });

  it("does nothing when selectedItemId doesn't match any chore", () => {
    const store = makeStore([makeChore()]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ChoresPage, {
      target,
      props: { store, floorStore: { floors: [] }, selectedItemId: "missing" },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")).toBeNull();

    unmount(comp);
  });
});

describe("ChoresPage — schedule health summary", () => {
  it("renders a bar per non-empty health bucket and the right stat numbers", () => {
    const now = Date.now();
    const chore1 = makeChore({ id: "c1", periodDays: 10 });
    const chore2 = makeChore({ id: "c2", periodDays: 10 });
    const chore3 = makeChore({ id: "c3", periodDays: 10 });
    const store = makeStore([chore1, chore2, chore3]);
    store.assignments = [
      // pct = (due - now) / periodMs; periodDays=10 -> periodMs = 864,000,000
      { id: "a1", choreId: "c1", roomId: null, nextDueDate: new Date(now + 9 * 86400000).toISOString() }, // pct ~0.9 -> on-track
      { id: "a2", choreId: "c2", roomId: null, nextDueDate: new Date(now + 3 * 86400000).toISOString() }, // pct ~0.3 -> due-soon
      { id: "a3", choreId: "c3", roomId: null, nextDueDate: new Date(now - 1 * 86400000).toISOString() }, // pct 0 -> overdue
    ] as typeof store.assignments;

    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelectorAll(".chart-card-wrap .stacked-segment")).toHaveLength(3);
    expect(target.querySelector(".ui-stat-value")?.textContent).toBe("3");
    expect(target.querySelector(".ui-stat-value.danger")?.textContent).toBe("33%");
    expect(target.querySelector(".ui-stat-value.success")?.textContent).toBe("33%");

    unmount(comp);
  });

  it("shows the empty-charts placeholder when there are no assignments", () => {
    const store = makeStore([makeChore()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".empty-charts")).not.toBeNull();
    expect(target.querySelector(".chart-card-wrap")).toBeNull();

    unmount(comp);
  });
});

describe("ChoresPage — health click-to-filter", () => {
  function makeThreeBucketStore() {
    const now = Date.now();
    const chore1 = makeChore({ id: "c1", name: "On track chore", periodDays: 10 });
    const chore2 = makeChore({ id: "c2", name: "Due soon chore", periodDays: 10 });
    const chore3 = makeChore({ id: "c3", name: "Overdue chore", periodDays: 10 });
    const store = makeStore([chore1, chore2, chore3]);
    store.assignments = [
      // All within the default "needs attention" 7-day cutoff, spanning the 3 health buckets.
      { id: "a1", choreId: "c1", roomId: null, nextDueDate: new Date(now + 6 * 86400000).toISOString() }, // pct 0.6 -> on-track
      { id: "a2", choreId: "c2", roomId: null, nextDueDate: new Date(now + 3 * 86400000).toISOString() }, // pct 0.3 -> due-soon
      { id: "a3", choreId: "c3", roomId: null, nextDueDate: new Date(now - 1 * 86400000).toISOString() }, // pct 0 -> overdue
    ] as typeof store.assignments;
    return store;
  }

  it("clicking the Overdue stat tile filters to overdue chores; clicking it again clears the filter", () => {
    const store = makeThreeBucketStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const overdueTile = Array.from(target.querySelectorAll(".ui-stat-tile")).find((el) => el.textContent?.includes("Overdue")) as HTMLElement;
    overdueTile.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);
    expect(target.querySelector(".name-cell")?.textContent).toContain("Overdue chore");
    expect(overdueTile.classList.contains("active")).toBe(true);

    overdueTile.click();
    flushSync();
    expect(overdueTile.classList.contains("active")).toBe(false);
    expect(target.querySelectorAll(".name-cell")).toHaveLength(3);

    unmount(comp);
  });

  it("clicking a bar chart segment filters to that bucket", () => {
    const store = makeThreeBucketStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const dueSoonSegment = Array.from(target.querySelectorAll(".stacked-segment")).find((el) => el.getAttribute("title")?.startsWith("Due soon")) as HTMLElement;
    dueSoonSegment.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);
    expect(target.querySelector(".name-cell")?.textContent).toContain("Due soon chore");

    unmount(comp);
  });

  it("clicking the Active tile clears any health filter", () => {
    const store = makeThreeBucketStore();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const overdueTile = Array.from(target.querySelectorAll(".ui-stat-tile")).find((el) => el.textContent?.includes("Overdue")) as HTMLElement;
    overdueTile.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);

    const activeTile = Array.from(target.querySelectorAll(".ui-stat-tile")).find((el) => el.textContent?.includes("Active")) as HTMLElement;
    activeTile.click();
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(3);
    expect(activeTile.classList.contains("active")).toBe(true);

    unmount(comp);
  });
});

describe("ChoresPage — schedule filter", () => {
  it("matches a literal daily chore under the Daily filter and an adaptive chore under Adaptive", () => {
    const dailyChore = makeChore({ id: "c1", name: "Water plants", frequencyType: "daily", frequency: 1, frequencyMetadata: {} });
    const adaptiveChore = makeChore({ id: "c2", name: "Change filter", frequencyType: "adaptive", frequency: 1, frequencyMetadata: {} });
    const store = makeStore([dailyChore, adaptiveChore]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();

    const scheduleSelect = Array.from(target.querySelectorAll("select")).find(
      (s) => Array.from(s.options).some((o) => o.value === "adaptive"),
    ) as HTMLSelectElement;

    scheduleSelect.value = "daily";
    scheduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);
    expect(target.querySelector(".name-cell")?.textContent).toContain("Water plants");

    scheduleSelect.value = "adaptive";
    scheduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(target.querySelectorAll(".name-cell")).toHaveLength(1);
    expect(target.querySelector(".name-cell")?.textContent).toContain("Change filter");

    unmount(comp);
  });
});

describe("ChoresPage — unassigned chores stay visible by default", () => {
  it("shows a freshly imported chore with no room assignment under the default attention filter", () => {
    const chore = makeChore({ id: "c1", name: "Imported chore" });
    const store = makeStore([chore]);
    // No assignments -- mirrors a Donetick import, which creates Chore rows only.
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".name-cell")?.textContent).toContain("Imported chore");
    expect(target.querySelector(".footer")?.textContent).toContain("1 chore");

    unmount(comp);
  });
});

describe("ChoresPage — due-filter toggle persists across remounts", () => {
  it("keeps the 'all chores' selection after the page is unmounted and remounted", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    let comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();
    expect(target.querySelector('button[title="Needs attention"]')?.className).toContain("active");

    (target.querySelector('button[title="All chores"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector('button[title="All chores"]')?.className).toContain("active");

    unmount(comp);
    target.innerHTML = "";
    comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector('button[title="All chores"]')?.className).toContain("active");
    expect(target.querySelector('button[title="Needs attention"]')?.className).not.toContain("active");

    unmount(comp);
  });
});

describe("ChoresPage — mark-all-done backdating", () => {
  it("shows a date picker defaulting to today, and confirms with only notes when left at today", async () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[title="Mark all done"]') as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector(".dp-input")).not.toBeNull();

    (target.querySelector(".ui-modal-footer .ui-button-primary") as HTMLButtonElement).click();
    await Promise.resolve();
    flushSync();

    expect(store.completeChore).toHaveBeenCalledWith("c1", "");

    unmount(comp);
  });

  it("confirms with notes and completedOn after picking a past date", async () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[title="Mark all done"]') as HTMLButtonElement).click();
    flushSync();

    (target.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    const cells = [...document.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const firstOfMonth = cells.find((c) => c.textContent === "1")!;
    firstOfMonth.click();
    flushSync();

    (target.querySelector(".ui-modal-footer .ui-button-primary") as HTMLButtonElement).click();
    await Promise.resolve();
    flushSync();

    expect(store.completeChore).toHaveBeenCalledTimes(1);
    const [id, notes, completedOn] = store.completeChore.mock.calls[0];
    expect(id).toBe("c1");
    expect(notes).toBe("");
    expect(completedOn).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    unmount(comp);
  });

});

describe("ChoresPage — responsive columns", () => {
  it("marks rooms hideBelow tablet and schedule hideBelow mobile, keeps actions always visible", () => {
    const store = makeStore([makeChore()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, schedule, rooms, nextDue, actions
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // rooms
    expect(headers[2].classList.contains("col-hide-mobile")).toBe(true); // schedule
    expect(headers[5].classList.contains("col-hide-tablet")).toBe(false); // actions
    expect(headers[5].classList.contains("col-hide-mobile")).toBe(false); // actions

    unmount(comp);
  });
});
