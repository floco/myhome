import { describe, it, expect, vi, afterEach } from "vitest";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const sampleDoc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: 100000, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [
    { id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: "build.phases.planning.description", descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
  ],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: "build.tasks.siteSurvey.description", descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 500, actualCost: 480, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
    { id: "t2", phaseId: "ph1", parentTaskId: null, displayOrder: 1, titleKey: "build.tasks.architecturalPlans.title", titleOverride: null, descriptionKey: "build.tasks.architecturalPlans.description", descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 2000, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
    { id: "t3", phaseId: "ph1", parentTaskId: null, displayOrder: 2, titleKey: "build.tasks.buildingPermits.title", titleOverride: null, descriptionKey: "build.tasks.buildingPermits.description", descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 0, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [
    { id: "d1", predecessorTaskId: "t1", successorTaskId: "t2" },
    { id: "d2", predecessorTaskId: "t2", successorTaskId: "t3" },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
  return createBuildStore(getHomeId);
}

afterEach(() => vi.unstubAllGlobals());

describe("buildStore", () => {
  it("loads the build document", async () => {
    const store = makeStore();
    await tick();
    expect(store.project?.id).toBe("p1");
    expect(store.phases).toHaveLength(1);
    expect(store.tasks).toHaveLength(3);
  });

  it("computes project budget as planned vs actual sums across tasks", async () => {
    const store = makeStore();
    await tick();
    expect(store.projectBudget.planned).toBe(2500);
    expect(store.projectBudget.actual).toBe(480);
  });

  it("computes phase progress as completed/total tasks", async () => {
    const store = makeStore();
    await tick();
    expect(store.phaseProgress("ph1")).toBeCloseTo(1 / 3);
  });

  it("marks a task with an incomplete predecessor as blocked", async () => {
    const store = makeStore();
    await tick();
    expect(store.taskReadyOrBlocked("t3")).toBe("blocked");
  });

  it("marks a task with a completed predecessor as ready", async () => {
    const store = makeStore();
    await tick();
    expect(store.taskReadyOrBlocked("t2")).toBe("ready");
  });

  it("startProject posts to /build/start and reloads", async () => {
    const store = makeStore();
    await tick();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    await store.startProject();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/homes/${HOME}/build/start`,
      expect.objectContaining({ method: "POST" })
    );
  });

  it("updateTask PUTs the patch and reloads", async () => {
    const store = makeStore();
    await tick();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    await store.updateTask("t2", { status: "in_progress" });
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/homes/${HOME}/build/tasks/t2`,
      expect.objectContaining({ method: "PUT" })
    );
  });
});
