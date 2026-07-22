import { _ } from "svelte-i18n";
import { get } from "svelte/store";

export interface Chore {
  id: string;
  donetickId: number | null;
  name: string;
  emoji: string;
  periodDays: number;
  frequencyType: string;
  frequency: number;
  frequencyMetadata: Record<string, unknown>;
  scheduleFromDue: boolean;
  nextDueDate: string;
  description: string;
  attachments: string[];
}

export interface CompletionRecord {
  id: string;
  choreId: string;
  assignmentId: string | null;
  completedAt: string;
  scheduledDue: string;
  notes: string;
}

export function scheduleLabel(chore: Chore): string {
  const { frequencyType: ft, frequency: n, frequencyMetadata: meta } = chore;
  const unit = (meta as Record<string, string>)?.unit ?? "days";
  const t = get(_);
  if (ft === "day_of_the_month") return t("chores.schedule.monthlyOnDay", { values: { n } });
  if (ft === "days_of_the_week") {
    const dayKeys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    const days = ((meta as Record<string, number[]>)?.days ?? []).map((d) => t(`chores.schedule.dayAbbrev.${dayKeys[(d - 1) % 7]}`));
    return days.length ? t("chores.schedule.weeklyOn", { values: { days: days.join(", ") } }) : t("chores.schedule.weekly");
  }
  if (ft === "weekly") return n === 1 ? t("chores.schedule.weekly") : t("chores.schedule.everyNWeeks", { values: { n } });
  if (ft === "monthly") return n === 1 ? t("chores.schedule.monthly") : t("chores.schedule.everyNMonths", { values: { n } });
  if (ft === "yearly") return n === 1 ? t("chores.schedule.yearly") : t("chores.schedule.everyNYears", { values: { n } });
  if (ft === "interval") {
    if (unit === "years") return n === 1 ? t("chores.schedule.yearly") : t("chores.schedule.everyNYears", { values: { n } });
    if (unit === "months") return n === 1 ? t("chores.schedule.monthly") : t("chores.schedule.everyNMonths", { values: { n } });
    if (unit === "weeks") return n === 1 ? t("chores.schedule.weekly") : t("chores.schedule.everyNWeeks", { values: { n } });
    if (n === 1) return t("chores.schedule.daily");
    if (n === 7) return t("chores.schedule.weekly");
    if (n === 14) return t("chores.schedule.everyNWeeks", { values: { n: 2 } });
    if (n === 30) return t("chores.schedule.monthly");
    if (n === 90) return t("chores.schedule.quarterly");
    if (n === 180) return t("chores.schedule.everyNMonths", { values: { n: 6 } });
    if (n === 365) return t("chores.schedule.yearly");
    if (n === 730) return t("chores.schedule.everyNYears", { values: { n: 2 } });
    return t("chores.schedule.everyNDays", { values: { n } });
  }
  return `${chore.periodDays}d`;
}

export interface Position {
  x: number;
  y: number;
}

export interface Assignment {
  id: string;
  choreId: string;
  roomId: string | null;
  position: Position | null;
  nextDueDate: string;
}

export interface ChoreDocument {
  version: number;
  chores: Chore[];
  assignments: Assignment[];
  completions: CompletionRecord[];
}

export function createChoreStore(getHomeId: () => string | null = () => null) {
  const chores = $state<Chore[]>([]);
  const assignments = $state<Assignment[]>([]);
  const completions = $state<CompletionRecord[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/chores`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: ChoreDocument = await resp.json();
      chores.length = 0;
      for (const c of doc.chores) chores.push(c);
      assignments.length = 0;
      for (const a of doc.assignments) assignments.push(a);
      completions.length = 0;
      for (const r of doc.completions ?? []) completions.push(r);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  function getProgress(assignment: Assignment, chore: Chore): number {
    const now = Date.now();
    const due = new Date(assignment.nextDueDate).getTime();
    const periodMs = chore.periodDays * 86400 * 1000;
    return Math.max(0, Math.min(1, (due - now) / periodMs));
  }

  function getColor(pct: number): string {
    if (pct > 0.5) return "#4caf50";
    if (pct > 0.25) return "#ff9800";
    return "#f44336";
  }

  function assignmentsForRoom(roomId: string): Assignment[] {
    return assignments.filter((a) => a.roomId === roomId);
  }

  function houseAssignments(): Assignment[] {
    return assignments.filter((a) => a.roomId === null);
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/chores/${id}/attachments`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(id: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores/${id}/attachments/${filename}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function createChore(data: Omit<Chore, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateChore(id: string, patch: Partial<Omit<Chore, "id" | "donetickId">>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteChore(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function completeChore(id: string, notes: string = ""): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores/${id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function importFromDonetick(token: string): Promise<number> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/chores/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const { imported } = await resp.json();
    await init();
    return imported as number;
  }

  async function completeAssignment(id: string, notes: string = ""): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/assignments/${id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  function getCompletionsForChore(choreId: string): CompletionRecord[] {
    return completions.filter((r) => r.choreId === choreId);
  }

  async function createAssignment(data: Omit<Assignment, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/assignments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateAssignmentPosition(id: string, position: Position): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/assignments/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function _putAssignmentDelay(id: string, days: number): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const assignment = assignments.find((a) => a.id === id);
    const base = assignment?.nextDueDate ? new Date(assignment.nextDueDate) : new Date();
    base.setDate(base.getDate() + days);
    const resp = await fetch(`/api/homes/${homeId}/assignments/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nextDueDate: base.toISOString() }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  }

  async function delayAssignment(id: string, days: number): Promise<void> {
    await _putAssignmentDelay(id, days);
    await init();
  }

  async function delayChore(choreId: string, days: number): Promise<void> {
    const choreAssignments = assignments.filter((a) => a.choreId === choreId);
    await Promise.all(choreAssignments.map((a) => _putAssignmentDelay(a.id, days)));
    await init();
  }

  async function deleteAssignment(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/assignments/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteCompletion(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/completions/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get chores() { return chores as Chore[]; },
    get assignments() { return assignments as Assignment[]; },
    get completions() { return completions as CompletionRecord[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    getProgress,
    getColor,
    assignmentsForRoom,
    houseAssignments,
    getCompletionsForChore,
    uploadAttachment,
    deleteAttachment,
    createChore,
    updateChore,
    deleteChore,
    completeChore,
    importFromDonetick,
    createAssignment,
    completeAssignment,
    updateAssignmentPosition,
    deleteAssignment,
    delayAssignment,
    delayChore,
    deleteCompletion,
    reload: init,
  };
}
