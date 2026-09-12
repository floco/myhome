import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoreEditModalWrapper from "./fixtures/ChoreEditModalWrapper.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1", donetickId: null, name: "Annual task", emoji: "📋",
    periodDays: 30, frequencyType: "day_of_the_month", frequency: 15,
    frequencyMetadata: { months: [5] }, scheduleFromDue: true,
    nextDueDate: "2027-05-15T00:00:00Z", description: "", attachments: [],
    ...overrides,
  };
}

function makeStore(overrides = {}) {
  return {
    updateChore: vi.fn().mockResolvedValue(undefined),
    deleteChore: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    getCompletionsForChore: vi.fn().mockReturnValue([]),
    assignments: [],
    deleteCompletion: vi.fn().mockResolvedValue(undefined),
    createAssignment: vi.fn().mockResolvedValue(undefined),
    updateAssignmentLabel: vi.fn().mockResolvedValue(undefined),
    deleteAssignment: vi.fn().mockResolvedValue(undefined),
    delayAssignment: vi.fn().mockResolvedValue(undefined),
    completeAssignment: vi.fn().mockResolvedValue(undefined),
    completeChore: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

const NO_ROOMS: Array<{ id: string; label: string; polygon: { x: number; y: number }[] | null }> = [];

afterEach(() => {
  document.body.innerHTML = "";
});

describe("ChoreEditModal — live due-date refresh across completions", () => {
  it("updates the current-due-date field when the chore prop is replaced with a freshly-completed one, without resetting the active tab", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();

    const initialChore = makeChore({ nextDueDate: "2027-05-15T00:00:00Z" });
    const updatedChore = makeChore({ nextDueDate: "2028-05-15T00:00:00Z" });

    const app = mount(ChoreEditModalWrapper, {
      target,
      props: { initialChore, updatedChore, store, rooms: NO_ROOMS },
    }) as unknown as { applyUpdate: () => void };
    flushSync();

    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toBe("05/15/2027");

    // Switch to the History tab -- this must survive the refresh below.
    const historyTab = Array.from(target.querySelectorAll("button.tab")).find((b) => b.textContent?.includes("History"));
    (historyTab as HTMLElement).click();
    flushSync();
    expect(target.querySelector("button.tab.active")?.textContent).toContain("History");

    // Simulate the parent (ChoresPage) handing down a freshly-refetched
    // chore object after a completion -- same id, advanced nextDueDate.
    app.applyUpdate();
    flushSync();

    // The active tab must survive the refresh -- a completion made from
    // within the modal (e.g. completing an assignment) must not yank the
    // user back to the Info tab.
    expect(target.querySelector("button.tab.active")?.textContent).toContain("History");

    const infoTab = Array.from(target.querySelectorAll("button.tab")).find((b) => b.textContent?.includes("Info"));
    (infoTab as HTMLElement).click();
    flushSync();
    expect((target.querySelector(".dp-input") as HTMLInputElement).value).toBe("05/15/2028");

    unmount(app as never);
    target.remove();
  });
});
