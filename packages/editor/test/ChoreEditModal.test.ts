import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import ChoreEditModal from "../src/lib/components/ChoreEditModal.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1",
    donetickId: null,
    name: "Sweep",
    emoji: "🧹",
    periodDays: 14,
    frequencyType: "interval",
    frequency: 14,
    frequencyMetadata: { unit: "days" },
    scheduleFromDue: false,
    nextDueDate: "2027-01-01T00:00:00Z",
    description: "",
    attachments: [],
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
    previewNextDue: vi.fn().mockResolvedValue("2027-02-01T00:00:00Z"),
    ...overrides,
  };
}

const NO_ROOMS: Array<{ id: string; label: string; polygon: { x: number; y: number }[] | null }> = [];
const SQUARE_ROOM = { id: "r1", label: "Kitchen", polygon: [{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 2, y: 2 }, { x: 0, y: 2 }] };

describe("ChoreEditModal — tabs", () => {
  it("shows Info and Media tab buttons when chore is provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Info");
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    unmount(app);
    target.remove();
  });

  it("clicking Media tab renders drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore({ attachments: ["photo.jpg"] }), store: makeStore(), rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("Save calls updateChore with form values", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const onclose = vi.fn();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose },
    });
    flushSync();
    const saveBtn = Array.from(target.querySelectorAll("button")).find(
      b => b.textContent?.trim() === "Save",
    ) as HTMLButtonElement;
    saveBtn.click();
    await tick();
    expect(store.updateChore).toHaveBeenCalledWith("c1", expect.objectContaining({ name: "Sweep" }));
    unmount(app);
    target.remove();
  });

  it("Delete button triggers confirm then calls deleteChore", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({ deleteChore: vi.fn().mockResolvedValue(undefined) });
    const onclose = vi.fn();
    mount(ChoreEditModal, { target, props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose } });
    flushSync();
    // Click delete → shows confirm
    const del = Array.from(target.querySelectorAll("button")).find(b => b.textContent?.includes("🗑")) as HTMLButtonElement;
    del.click(); flushSync();
    expect(target.textContent).toContain("Delete this chore?");
    // Confirm
    const confirm = Array.from(target.querySelectorAll("button")).find(b => b.textContent?.trim() === "Confirm delete") as HTMLButtonElement;
    confirm.click(); await tick();
    expect(store.deleteChore).toHaveBeenCalledWith("c1");
    target.remove();
  });

  it("seeds the recurrence picker from the chore's existing schedule and saves changes to it", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore({ frequencyType: "yearly", frequency: 1, frequencyMetadata: {} }), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();

    const categorySelect = target.querySelector("#se-category") as HTMLSelectElement;
    expect(categorySelect.value).toBe("yearly");

    categorySelect.value = "daily";
    categorySelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find(
      b => b.textContent?.trim() === "Save",
    ) as HTMLButtonElement;
    saveBtn.click();
    await tick();
    expect(store.updateChore).toHaveBeenCalledWith("c1", expect.objectContaining({
      frequencyType: "daily", frequency: 1, frequencyMetadata: {},
    }));
    unmount(app);
    target.remove();
  });

  it("disables Save when the recurrence picker is in an invalid state", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore({ frequencyType: "days_of_the_week", frequency: 1, frequencyMetadata: { days: [1] } }), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();

    // Deselect the only selected day -> no days selected -> invalid.
    const monButton = Array.from(target.querySelectorAll(".day-toggle")).find((b) => b.textContent === "Mon") as HTMLButtonElement;
    monButton.click();
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find(
      b => b.textContent?.trim() === "Save",
    ) as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);
    unmount(app);
    target.remove();
  });

  it("keeps the Save button visible when switching to non-info tabs", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();
    for (const tabText of ["Assignments", "Media", "History"]) {
      const tab = Array.from(target.querySelectorAll(".tab")).find(
        (t) => t.textContent?.includes(tabText),
      ) as HTMLButtonElement;
      tab.click();
      flushSync();
      const saveBtn = Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Save",
      );
      expect(saveBtn, `Save button missing on ${tabText} tab`).toBeDefined();
    }
    unmount(app);
    target.remove();
  });

  it("orders the footer buttons complete-all, go-to-assignments, Delete, Cancel, Save on every tab (go-to-assignments hidden on the Assignments tab itself)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();
    const expectedByTab: Record<string, string[]> = {
      Info: ["✓", "→", "🗑 Delete", "Cancel", "Save"],
      Assignments: ["✓", "🗑 Delete", "Cancel", "Save"],
      Media: ["✓", "→", "🗑 Delete", "Cancel", "Save"],
      History: ["✓", "→", "🗑 Delete", "Cancel", "Save"],
    };
    for (const tabText of ["Info", "Assignments", "Media", "History"]) {
      const tab = Array.from(target.querySelectorAll(".tab")).find(
        (t) => t.textContent?.includes(tabText),
      ) as HTMLButtonElement;
      tab.click();
      flushSync();
      const footerLabels = Array.from(target.querySelectorAll(".ui-modal-footer button")).map(
        (b) => b.textContent?.trim(),
      );
      expect(footerLabels, `footer order wrong on ${tabText} tab`).toEqual(expectedByTab[tabText]);
    }
    unmount(app);
    target.remove();
  });

  it("does not show a Place on map button in the footer, even on the Info tab", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn(), onplaceonmap: vi.fn() },
    });
    flushSync();
    const footerText = target.querySelector(".ui-modal-footer")?.textContent ?? "";
    expect(footerText).not.toContain("Place on map");
    unmount(app);
    target.remove();
  });

  it("shows Place on map in the Assignments tab body and calls onplaceonmap with the chore id", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const onplaceonmap = vi.fn();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn(), onplaceonmap },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();
    const placeBtn = Array.from(target.querySelectorAll(".assignments-pane button")).find(
      (b) => b.textContent?.includes("Place on map"),
    ) as HTMLButtonElement;
    expect(placeBtn).toBeDefined();
    placeBtn.click();
    expect(onplaceonmap).toHaveBeenCalledWith("c1");
    unmount(app);
    target.remove();
  });

  it("shows the emoji picker and name input on the same row, emoji first", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();
    const row = target.querySelector(".name-emoji-row");
    expect(row).not.toBeNull();
    const [emojiField, nameField] = Array.from(row!.children);
    expect(emojiField.querySelector(".ep-trigger")).not.toBeNull();
    expect(nameField.querySelector("#chore-name, input")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("sorts the assignment room picker alphabetically regardless of input order", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const rooms = [
      { id: "r1", label: "Zebra room", polygon: null },
      { id: "r2", label: "Attic", polygon: null },
      { id: "r3", label: "Master bedroom", polygon: null },
    ];
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms, onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();
    const options = Array.from(target.querySelectorAll(".add-assignment-row select option")).map(o => o.textContent);
    expect(options.slice(1)).toEqual(["Attic", "Master bedroom", "Zebra room"]);
    unmount(app);
    target.remove();
  });
});

describe("ChoreEditModal — schedule anchor + next-due preview", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the due-date/completion-date radio options instead of a checkbox, checked to match the chore", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore({ scheduleFromDue: true }), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();

    expect(target.querySelector('input[type="checkbox"]#sfd-modal')).toBeNull();
    const dueRadio = target.querySelector("#edit-sfd-due") as HTMLInputElement;
    const completionRadio = target.querySelector("#edit-sfd-completion") as HTMLInputElement;
    expect(dueRadio.checked).toBe(true);
    expect(completionRadio.checked).toBe(false);

    unmount(app);
    target.remove();
  });

  it("selecting 'schedule from completion date' and saving sends scheduleFromDue: false", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore({ scheduleFromDue: true }), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();

    const completionRadio = target.querySelector("#edit-sfd-completion") as HTMLInputElement;
    completionRadio.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find(
      b => b.textContent?.trim() === "Save",
    ) as HTMLButtonElement;
    saveBtn.click();
    await tick();
    expect(store.updateChore).toHaveBeenCalledWith("c1", expect.objectContaining({ scheduleFromDue: false }));

    unmount(app);
    target.remove();
  });

  it("shows a live computed next-due preview from previewNextDue", async () => {
    vi.useFakeTimers();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({ previewNextDue: vi.fn().mockResolvedValue("2027-02-01T00:00:00Z") });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();

    await vi.advanceTimersByTimeAsync(300);
    flushSync();

    expect(store.previewNextDue).toHaveBeenCalledWith(expect.objectContaining({
      frequencyType: "interval", frequency: 14, scheduleFromDue: false,
    }));
    expect(target.querySelector(".next-due-preview-value")?.textContent).toBe("02/01/2027");

    unmount(app);
    target.remove();
  });
});

describe("ChoreEditModal — Assignments tab", () => {
  it("lists existing assignments with their label and room, and completes/delays/deletes them", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [
        { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 1 }, nextDueDate: "2027-01-01T00:00:00Z", label: "Balcony plants" },
      ],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();

    const assignmentsTab = Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement;
    assignmentsTab.click();
    flushSync();

    expect(target.querySelector(".assign-where")?.textContent).toBe("Kitchen");
    expect((target.querySelector(".assign-label-input") as HTMLInputElement).value).toBe("Balcony plants");

    const [completeBtn, delayBtn, deleteBtn] = Array.from(target.querySelectorAll(".assignment-row .icon-btn")) as HTMLButtonElement[];
    delayBtn.click();
    expect(store.delayAssignment).toHaveBeenCalledWith("a1", 7);
    deleteBtn.click();
    expect(store.deleteAssignment).toHaveBeenCalledWith("a1");

    completeBtn.click();
    flushSync();
    expect(target.querySelector(".complete-form")).not.toBeNull(); // ChoreCompleteModal is open

    unmount(app);
    target.remove();
  });

  it("groups the assignment row's action buttons together so they wrap as a unit", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [
        { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 1 }, nextDueDate: "2027-01-01T00:00:00Z", label: "Balcony plants" },
      ],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();

    const row = target.querySelector(".assignment-row")!;
    const actions = row.querySelector(".assignment-actions");
    expect(actions).not.toBeNull();
    expect(actions?.querySelectorAll(".icon-btn").length).toBe(3);

    unmount(app);
    target.remove();
  });

  it("editing the label input blur calls updateAssignmentLabel only when changed", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [{ id: "a1", choreId: "c1", roomId: "r1", position: null, nextDueDate: "2027-01-01T00:00:00Z", label: "Side A" }],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();

    const input = target.querySelector(".assign-label-input") as HTMLInputElement;
    input.value = "Side A";
    input.dispatchEvent(new Event("blur"));
    await tick();
    expect(store.updateAssignmentLabel).not.toHaveBeenCalled();

    input.value = "Side A (near window)";
    input.dispatchEvent(new Event("blur"));
    await tick();
    expect(store.updateAssignmentLabel).toHaveBeenCalledWith("a1", "Side A (near window)");

    unmount(app);
    target.remove();
  });

  it("adding an assignment computes position as the room's polygon centroid", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();

    const roomSelect = target.querySelector(".add-assignment-row select") as HTMLSelectElement;
    roomSelect.value = "r1";
    roomSelect.dispatchEvent(new Event("change", { bubbles: true }));
    const labelInput = target.querySelector(".add-assignment-row .assign-label-input") as HTMLInputElement;
    labelInput.value = "New spot";
    labelInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const addBtn = Array.from(target.querySelectorAll(".add-assignment-row button")).find(b => b.textContent?.trim() === "Add") as HTMLButtonElement;
    addBtn.click();
    await tick();

    expect(store.createAssignment).toHaveBeenCalledWith({
      choreId: "c1", roomId: "r1", position: { x: 1, y: 1 }, nextDueDate: "", label: "New spot",
    });

    unmount(app);
    target.remove();
  });

  it("shows an assignment count badge on the tab when assignments exist", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [{ id: "a1", choreId: "c1", roomId: "r1", position: null, nextDueDate: "2027-01-01T00:00:00Z", label: null }],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();

    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Assignments (1)");

    unmount(app);
    target.remove();
  });
});

describe("ChoreEditModal — History tab", () => {
  it("sorts completions by completedAt descending even when a backdated one is inserted out of order", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      // Noon UTC (not midnight) so the rendered calendar date is stable regardless of the test machine's local timezone.
      getCompletionsForChore: vi.fn().mockReturnValue([
        { id: "r1", choreId: "c1", assignmentId: null, completedAt: "2026-08-01T12:00:00Z", scheduledDue: "", notes: "" },
        { id: "r2", choreId: "c1", assignmentId: null, completedAt: "2026-07-01T12:00:00Z", scheduledDue: "", notes: "" }, // backdated, inserted after r1 but earlier in time
        { id: "r3", choreId: "c1", assignmentId: null, completedAt: "2026-08-15T12:00:00Z", scheduledDue: "", notes: "" },
      ]),
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("History")) as HTMLButtonElement).click();
    flushSync();

    const dates = Array.from(target.querySelectorAll(".hist-date")).map(el => el.textContent);
    // Default test locale is "en" -> MDY date format (see localization.ts LANGUAGE_DEFAULTS)
    expect(dates).toEqual(["08/15/2026", "08/01/2026", "07/01/2026"]);

    unmount(app);
    target.remove();
  });

  it("shows the assignment's label next to the room name, and no time-of-day", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [{ id: "a1", choreId: "c1", roomId: "r1", position: null, nextDueDate: "2027-01-01T00:00:00Z", label: "Balcony plants" }],
      getCompletionsForChore: vi.fn().mockReturnValue([
        { id: "r1", choreId: "c1", assignmentId: "a1", completedAt: "2026-08-01T12:00:00Z", scheduledDue: "", notes: "" },
      ]),
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [{ id: "r1", label: "Kitchen", polygon: null }], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("History")) as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector(".hist-room")?.textContent).toContain("Kitchen");
    expect(target.querySelector(".hist-label")?.textContent).toBe("(Balcony plants)");
    expect(target.querySelector(".hist-date")?.textContent).toBe("08/01/2026");

    unmount(app);
    target.remove();
  });
});

describe("ChoreEditModal — footer completion actions", () => {
  it("clicking Complete All then confirming calls store.completeChore for the whole chore", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({ completeChore: vi.fn().mockResolvedValue(undefined) });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();

    const completeAllBtn = target.querySelector(".footer-complete-all") as HTMLButtonElement;
    expect(completeAllBtn).not.toBeNull();
    completeAllBtn.click();
    flushSync();
    expect(target.querySelector(".complete-form")).not.toBeNull();

    const confirmBtn = Array.from(target.querySelectorAll("button")).find(
      b => b.textContent?.trim() === "Mark done",
    ) as HTMLButtonElement;
    confirmBtn.click();
    await tick();

    expect(store.completeChore).toHaveBeenCalledWith("c1", "");
    unmount(app);
    target.remove();
  });

  it("clicking Go to assignments switches to the Assignments tab", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();

    const goToAssignmentsBtn = target.querySelector(".footer-go-to-assignments") as HTMLButtonElement;
    expect(goToAssignmentsBtn).not.toBeNull();
    goToAssignmentsBtn.click();
    flushSync();

    const activeTab = target.querySelector(".tab.active");
    expect(activeTab?.textContent).toContain("Assignments");

    unmount(app);
    target.remove();
  });

  it("hides Go to assignments once already on the Assignments tab", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store: makeStore(), rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find(t => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector(".footer-go-to-assignments")).toBeNull();

    unmount(app);
    target.remove();
  });
});
