import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoresPage from "../src/lib/components/ChoresPage.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";
import { choreFilterState } from "../src/lib/choreFilterState.svelte";

afterEach(() => {
  document.body.innerHTML = "";
  choreFilterState.dueFilter = "all"; // module-level state -- reset so it doesn't leak between tests
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
    skipChore: vi.fn(),
    delayChore: vi.fn(),
    createAssignment: vi.fn(),
    updateAssignmentPosition: vi.fn(),
    updateAssignmentLabel: vi.fn(),
    removeAssignment: vi.fn(),
    deleteAssignment: vi.fn(),
    delayAssignment: vi.fn(),
    completeAssignment: vi.fn(),
    skipAssignment: vi.fn(),
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

describe("ChoresPage — overdue due-date styling", () => {
  it("marks the Next due cell overdue for a past-due chore but not for an upcoming one", () => {
    const now = Date.now();
    const overdueChore = makeChore({ id: "c1", name: "Overdue chore" });
    const upcomingChore = makeChore({ id: "c2", name: "Upcoming chore" });
    const store = makeStore([overdueChore, upcomingChore]);
    store.assignments = [
      { id: "a1", choreId: "c1", roomId: null, nextDueDate: new Date(now - 2 * 86400000).toISOString() },
      { id: "a2", choreId: "c2", roomId: null, nextDueDate: new Date(now + 2 * 86400000).toISOString() },
    ] as typeof store.assignments;

    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    const rows = target.querySelectorAll("tbody tr");
    expect(rows[0].querySelector(".overdue-due")).not.toBeNull();
    expect(rows[1].querySelector(".overdue-due")).toBeNull();

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

describe("ChoresPage — unassigned chores stay visible under the attention filter", () => {
  it("shows a freshly imported chore with no room assignment even with the needs-attention checkbox on", () => {
    const chore = makeChore({ id: "c1", name: "Imported chore" });
    const store = makeStore([chore]);
    // No assignments -- mirrors a Donetick import, which creates Chore rows only.
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();
    const checkbox = target.querySelector('.checkbox-row input[type="checkbox"]') as HTMLInputElement;
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".name-cell")?.textContent).toContain("Imported chore");
    expect(target.querySelector(".footer")?.textContent).toContain("1 chore");

    unmount(comp);
  });
});

describe("ChoresPage — due-filter checkbox persists across remounts", () => {
  it("keeps the needs-attention selection after the page is unmounted and remounted", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    let comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();
    let checkbox = target.querySelector('.checkbox-row input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(choreFilterState.dueFilter).toBe("attention");

    unmount(comp);
    target.innerHTML = "";
    comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();
    checkbox = target.querySelector('.checkbox-row input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);

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

describe("ChoresPage — delay/skip menu", () => {
  it("opens a menu offering week/month/year delay and skip-to-next, wired to the store", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[title="Delay or skip all assignments"]') as HTMLButtonElement).click();
    flushSync();

    const items = Array.from(document.querySelectorAll(".dsm-item")) as HTMLButtonElement[];
    const labels = items.map((b) => b.textContent);
    expect(labels).toEqual(["Delay by 1 week", "Delay by 1 month", "Delay by 1 year", "Skip to next occurrence"]);

    items.find((b) => b.textContent === "Delay by 1 month")!.click();
    expect(store.delayChore).toHaveBeenCalledWith("c1", "month");

    unmount(comp);
  });

  it("calls skipChore, not completeChore, from the skip menu item", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (target.querySelector('button[title="Delay or skip all assignments"]') as HTMLButtonElement).click();
    flushSync();
    (Array.from(document.querySelectorAll(".dsm-item")).find((b) => b.textContent === "Skip to next occurrence") as HTMLButtonElement).click();

    expect(store.skipChore).toHaveBeenCalledWith("c1");
    expect(store.completeChore).not.toHaveBeenCalled();

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
    // emoji, name, schedule, rooms, nextDue, attachments, actions
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // rooms
    expect(headers[2].classList.contains("col-hide-mobile")).toBe(true); // schedule
    expect(headers[6].classList.contains("col-hide-tablet")).toBe(false); // actions
    expect(headers[6].classList.contains("col-hide-mobile")).toBe(false); // actions

    unmount(comp);
  });
});

describe("ChoresPage — calendar view toggle", () => {
  it("shows the table by default and switches to the calendar grid when the Calendar tab is clicked", () => {
    const store = makeStore([makeChore()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".table-wrapper")).not.toBeNull();
    expect(target.querySelector(".cal-grid")).toBeNull();

    const calendarTab = Array.from(target.querySelectorAll(".tab")).find((b) => b.textContent === "Calendar") as HTMLButtonElement;
    calendarTab.click();
    flushSync();

    expect(target.querySelector(".table-wrapper")).toBeNull();
    expect(target.querySelector(".cal-grid")).not.toBeNull();

    unmount(comp);
  });

  it("opens the edit modal when a calendar chip is clicked", () => {
    const chore = makeChore({ id: "c1" });
    const store = makeStore([chore]);
    store.assignments = [
      { id: "a1", choreId: "c1", roomId: null, nextDueDate: "2026-08-15T12:00:00.000Z" },
    ] as typeof store.assignments;
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    (Array.from(target.querySelectorAll(".tab")).find((b) => b.textContent === "Calendar") as HTMLButtonElement).click();
    flushSync();
    // The calendar opens on the current month, which won't show the August chip -- jump to it via the month select.
    const monthSelect = target.querySelectorAll(".cal-select")[0] as HTMLSelectElement;
    const yearSelect = target.querySelectorAll(".cal-select")[1] as HTMLSelectElement;
    monthSelect.value = "7";
    monthSelect.dispatchEvent(new Event("change", { bubbles: true }));
    yearSelect.value = "2026";
    yearSelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    (target.querySelector(".cal-chip") as HTMLButtonElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("🧹 Sweep kitchen");

    unmount(comp);
  });
});
