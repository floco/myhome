import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import TaskModal from "../src/lib/components/TaskModal.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";

const HOME = "home-1";
const getHomeId = () => HOME;

const doc = {
  version: 1,
  project: { id: "p1", status: "in_progress", plannedStartDate: null, plannedCompletionDate: null, actualCompletionDate: null, plannedBudget: null, notes: "", createdAt: "2026-01-01T00:00:00+00:00", updatedAt: "2026-01-01T00:00:00+00:00" },
  phases: [{ id: "ph1", displayOrder: 0, nameKey: "build.phases.planning.name", nameOverride: null, descriptionKey: null, descriptionOverride: null, status: "in_progress", plannedStartDate: null, plannedEndDate: null, actualStartDate: null, actualEndDate: null }],
  tasks: [
    { id: "t1", phaseId: "ph1", parentTaskId: null, displayOrder: 0, titleKey: "build.tasks.siteSurvey.title", titleOverride: null, descriptionKey: "build.tasks.siteSurvey.description", descriptionOverride: null, status: "not_started", plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null, plannedCost: 500, actualCost: null, contractorId: null, validationRequired: true, validationStatus: "pending_validation", notes: "", attachments: [] },
  ],
  dependencies: [],
};

async function waitTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function setup() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
  const store = createBuildStore(getHomeId);
  const target = document.createElement("div");
  document.body.appendChild(target);
  return { store, target };
}

describe("TaskModal", () => {
  it("shows the resolved i18n title for a seeded task with no override", async () => {
    const { store, target } = setup();
    await waitTick();
    const comp = mount(TaskModal, { target, props: { task: store.tasks[0], store, onclose: vi.fn() } });
    await tick();
    flushSync();

    const input = target.querySelector("input.task-title-input") as HTMLInputElement;
    expect(input.value).toBe("Site Survey");

    unmount(comp);
    target.remove();
  });

  it("shows the validation status field when validationRequired is true", async () => {
    const { store, target } = setup();
    await waitTick();
    const comp = mount(TaskModal, { target, props: { task: store.tasks[0], store, onclose: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".validation-status-row")).toBeTruthy();

    unmount(comp);
    target.remove();
  });

  it("save calls store.updateTask with the patch", async () => {
    const { store, target } = setup();
    await waitTick();
    const onclose = vi.fn();
    const comp = mount(TaskModal, { target, props: { task: store.tasks[0], store, onclose } });
    await tick();
    flushSync();

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Save")!;
    saveBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await waitTick();
    flushSync();

    expect(fetchMock).toHaveBeenCalledWith(
      `/api/homes/${HOME}/build/tasks/t1`,
      expect.objectContaining({ method: "PUT" })
    );

    unmount(comp);
    target.remove();
  });
});
