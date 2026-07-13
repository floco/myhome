import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoresPage from "../src/lib/components/ChoresPage.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

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
    createAssignment: vi.fn(),
    updateAssignmentPosition: vi.fn(),
    removeAssignment: vi.fn(),
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

describe("ChoresPage — expand/collapse assignments", () => {
  it("expands and collapses the assignment detail row on toggle click", () => {
    const chore = makeChore();
    const store = makeStore([chore]);
    store.assignments = [{ id: "a1", choreId: "c1", roomId: null, nextDueDate: new Date().toISOString() }] as typeof store.assignments;
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ChoresPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".assign-row")).toBeNull();

    const toggleBtn = target.querySelector(".expand-btn") as HTMLButtonElement;
    toggleBtn.click();
    flushSync();
    expect(target.querySelector(".assign-row")).not.toBeNull();
    expect(target.querySelector(".assign-where")?.textContent).toBe("🏠 Whole house");

    toggleBtn.click();
    flushSync();
    expect(target.querySelector(".assign-row")).toBeNull();

    unmount(comp);
  });
});

describe("ChoresPage — schedule health summary", () => {
  it("renders a donut segment per non-empty health bucket and the right stat numbers", () => {
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

    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(3);
    expect(target.querySelector(".stat-value")?.textContent).toBe("3");
    expect(target.querySelector(".stat-value.overdue")?.textContent).toBe("1");
    expect(target.querySelector(".stat-value.ontrack")?.textContent).toBe("33%");

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
