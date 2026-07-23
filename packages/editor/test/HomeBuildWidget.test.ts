import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeBuildWidget from "../src/lib/components/HomeBuildWidget.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const emptyDoc = { version: 1, project: null, phases: [], tasks: [], dependencies: [] };

const seededDoc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: 100000, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [{ id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null }],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 500, actualCost: 480, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
    { id: "t2", phaseId: "ph1", parentTaskId: null, displayOrder: 1, titleKey: "build.tasks.architecturalPlans.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 2000, actualCost: null, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeBuildWidget", () => {
  it("renders nothing when there is no build project", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc }));
    const buildStore = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeBuildWidget, { target, props: { buildStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".widget")).toBeFalsy();

    unmount(comp);
    target.remove();
  });

  it("shows progress and budget once a project exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => seededDoc }));
    const buildStore = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeBuildWidget, { target, props: { buildStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".widget")).toBeTruthy();
    expect(target.textContent).toContain("50%");

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => seededDoc }));
    const buildStore = createBuildStore(getHomeId);
    await waitTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeBuildWidget, { target, props: { buildStore, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
