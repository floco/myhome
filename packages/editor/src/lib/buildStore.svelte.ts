// packages/editor/src/lib/buildStore.svelte.ts

export type BuildProjectStatus = "planning" | "in_progress" | "completed" | "on_hold";
export type BuildPhaseStatus = "not_started" | "in_progress" | "completed";
export type BuildTaskStatus = "not_started" | "ready" | "in_progress" | "waiting" | "blocked" | "completed";
export type ValidationStatus = "not_required" | "pending_validation" | "passed" | "failed";

export interface BuildProject {
  id: string;
  status: BuildProjectStatus;
  plannedStartDate: string | null;
  plannedCompletionDate: string | null;
  actualCompletionDate: string | null;
  plannedBudget: number | null;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export interface BuildPhase {
  id: string;
  displayOrder: number;
  nameKey: string | null;
  nameOverride: string | null;
  descriptionKey: string | null;
  descriptionOverride: string | null;
  status: BuildPhaseStatus;
  plannedStartDate: string | null;
  plannedEndDate: string | null;
  actualStartDate: string | null;
  actualEndDate: string | null;
}

export interface BuildTask {
  id: string;
  phaseId: string;
  parentTaskId: string | null;
  displayOrder: number;
  titleKey: string | null;
  titleOverride: string | null;
  descriptionKey: string | null;
  descriptionOverride: string | null;
  status: BuildTaskStatus;
  plannedStartDate: string | null;
  plannedDueDate: string | null;
  actualCompletionDate: string | null;
  plannedCost: number | null;
  actualCost: number | null;
  contractorId: string | null;
  validationRequired: boolean;
  validationStatus: ValidationStatus;
  notes: string;
  attachments: string[];
}

export interface BuildTaskDependency {
  id: string;
  predecessorTaskId: string;
  successorTaskId: string;
}

export interface BuildDocument {
  version: number;
  project: BuildProject | null;
  phases: BuildPhase[];
  tasks: BuildTask[];
  dependencies: BuildTaskDependency[];
}

export function createBuildStore(getHomeId: () => string | null = () => null) {
  const phases = $state<BuildPhase[]>([]);
  const tasks = $state<BuildTask[]>([]);
  const dependencies = $state<BuildTaskDependency[]>([]);
  let project = $state<BuildProject | null>(null);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/build`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: BuildDocument = await resp.json();
      project = doc.project;
      phases.length = 0;
      for (const p of doc.phases) phases.push(p);
      tasks.length = 0;
      for (const t of doc.tasks) tasks.push(t);
      dependencies.length = 0;
      for (const d of doc.dependencies) dependencies.push(d);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function startProject(plannedStartDate?: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plannedStartDate ? { plannedStartDate } : {}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateProject(patch: Partial<BuildProject>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/project`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteProject(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/project`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updatePhase(phaseId: string, patch: Partial<BuildPhase>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/phases/${phaseId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function createTask(data: { phaseId: string; titleOverride: string; [key: string]: unknown }): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateTask(taskId: string, patch: Partial<BuildTask>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteTask(taskId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function addDependency(predecessorTaskId: string, successorTaskId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/dependencies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ predecessorTaskId, successorTaskId }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function removeDependency(dependencyId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/dependencies/${dependencyId}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(taskId: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}/attachments`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(taskId: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/build/tasks/${taskId}/attachments/${filename}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  function phaseTasks(phaseId: string): BuildTask[] {
    return tasks.filter((t) => t.phaseId === phaseId);
  }

  function phaseBudget(phaseId: string): { planned: number; actual: number } {
    const ts = phaseTasks(phaseId);
    return {
      planned: ts.reduce((sum, t) => sum + (t.plannedCost ?? 0), 0),
      actual: ts.reduce((sum, t) => sum + (t.actualCost ?? 0), 0),
    };
  }

  function phaseProgress(phaseId: string): number {
    const ts = phaseTasks(phaseId);
    if (ts.length === 0) return 0;
    return ts.filter((t) => t.status === "completed").length / ts.length;
  }

  function taskReadyOrBlocked(taskId: string): BuildTaskStatus {
    const task = tasks.find((t) => t.id === taskId);
    if (!task) throw new Error(`Unknown taskId ${taskId}`);
    if (!["not_started", "ready", "blocked"].includes(task.status)) return task.status;
    const predecessorIds = dependencies.filter((d) => d.successorTaskId === taskId).map((d) => d.predecessorTaskId);
    if (predecessorIds.length === 0) return "ready";
    const allDone = predecessorIds.every((id) => tasks.find((t) => t.id === id)?.status === "completed");
    return allDone ? "ready" : "blocked";
  }

  const projectBudget = $derived({
    planned: tasks.reduce((sum, t) => sum + (t.plannedCost ?? 0), 0),
    actual: tasks.reduce((sum, t) => sum + (t.actualCost ?? 0), 0),
  });

  const projectProgress = $derived(
    tasks.length === 0 ? 0 : tasks.filter((t) => t.status === "completed").length / tasks.length
  );

  init();

  return {
    get project() { return project; },
    get phases() { return phases as BuildPhase[]; },
    get tasks() { return tasks as BuildTask[]; },
    get dependencies() { return dependencies as BuildTaskDependency[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    get projectBudget() { return projectBudget; },
    get projectProgress() { return projectProgress; },
    phaseTasks,
    phaseBudget,
    phaseProgress,
    taskReadyOrBlocked,
    startProject,
    updateProject,
    deleteProject,
    updatePhase,
    createTask,
    updateTask,
    deleteTask,
    addDependency,
    removeDependency,
    uploadAttachment,
    deleteAttachment,
    reload: init,
  };
}
