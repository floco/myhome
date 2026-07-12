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
