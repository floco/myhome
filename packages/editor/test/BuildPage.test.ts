import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import BuildPage from "../src/lib/components/BuildPage.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const emptyDoc = { version: 1, project: null, phases: [], tasks: [], dependencies: [] };

const seededDoc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: 100000, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [
    { id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null },
  ],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: null, descriptionOverride: null, status: "completed", plannedStartDate: null, plannedDueDate: "2020-01-01", actualCompletionDate: null, plannedCost: 500, actualCost: 480, contractorId: null, validationRequired: false, validationStatus: "not_required", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function renderPage(doc: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
  const store = createBuildStore(getHomeId);
  const target = document.createElement("div");
  document.body.appendChild(target);
  return { store, target };
}

afterEach(() => vi.unstubAllGlobals());

describe("BuildPage", () => {
  it("shows the start-tracking empty state when no project exists", async () => {
    const { store, target } = renderPage(emptyDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".start-card")).toBeTruthy();

    unmount(comp);
    target.remove();
  });

  it("shows the dashboard tab with stat tiles once a project exists", async () => {
    const { store, target } = renderPage(seededDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".start-card")).toBeFalsy();
    const values = Array.from(target.querySelectorAll(".ui-stat-value")).map((el) => el.textContent);
    expect(values.length).toBeGreaterThan(0);

    unmount(comp);
    target.remove();
  });

  it("switches to the phases tab on click", async () => {
    const { store, target } = renderPage(seededDoc);
    await waitTick();
    const comp = mount(BuildPage, { target, props: { store, onopentask: vi.fn() } });
    await tick();
    flushSync();

    const tabs = Array.from(target.querySelectorAll(".tab-bar .tab"));
    const phasesTab = tabs.find((el) => el.textContent?.includes("Phases")) as HTMLElement;
    phasesTab.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".phase-section")).toBeTruthy();

    unmount(comp);
    target.remove();
  });
});
