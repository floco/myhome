import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import PhaseSection from "../src/lib/components/PhaseSection.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const doc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: null, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [
    { id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
    { id: "ph2", displayOrder: 1, nameKey: "build.phases.foundation.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
  ],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: null, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
    { id: "t2", phaseId: "ph1", parentTaskId: null, displayOrder: 1, titleKey: "build.tasks.architecturalPlans.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: null, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("PhaseSection", () => {
  it("renders one collapsed phase-section per phase", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PhaseSection, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelectorAll(".phase-section")).toHaveLength(2);
    expect(target.querySelectorAll(".phase-tasks").length).toBe(0);

    unmount(comp);
    target.remove();
  });

  it("expands a phase to show its tasks on click", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PhaseSection, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    (target.querySelector(".phase-header") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const taskRows = target.querySelectorAll(".phase-tasks .task-row");
    expect(taskRows).toHaveLength(2);

    unmount(comp);
    target.remove();
  });

  it("clicking a task row calls onopentask with its id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onopentask = vi.fn();
    const comp = mount(PhaseSection, { target, props: { store, onopentask } });
    await tick();
    flushSync();

    (target.querySelector(".phase-header") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    (target.querySelector(".task-row") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onopentask).toHaveBeenCalledWith("t1");

    unmount(comp);
    target.remove();
  });
});
