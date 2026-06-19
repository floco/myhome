export interface Chore {
  id: string;
  donetickId: number | null;
  name: string;
  emoji: string;
  periodDays: number;
  frequencyType: string;
  frequency: number;
  frequencyMetadata: Record<string, unknown>;
  nextDueDate: string;
  description: string;
}

export function scheduleLabel(chore: Chore): string {
  const { frequencyType: ft, frequency: n, frequencyMetadata: meta } = chore;
  const unit = (meta as Record<string, string>)?.unit ?? "days";
  if (ft === "day_of_the_month") return `Monthly on day ${n}`;
  if (ft === "days_of_the_week") {
    const names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const days = ((meta as Record<string, number[]>)?.days ?? []).map((d) => names[(d - 1) % 7]);
    return days.length ? `Weekly on ${days.join(", ")}` : "Weekly";
  }
  if (ft === "weekly") return n === 1 ? "Weekly" : `Every ${n} weeks`;
  if (ft === "monthly") return n === 1 ? "Monthly" : `Every ${n} months`;
  if (ft === "yearly") return n === 1 ? "Yearly" : `Every ${n} years`;
  if (ft === "interval") {
    if (unit === "years") return n === 1 ? "Yearly" : `Every ${n} years`;
    if (unit === "months") return n === 1 ? "Monthly" : `Every ${n} months`;
    if (unit === "weeks") return n === 1 ? "Weekly" : `Every ${n} weeks`;
    if (n === 1) return "Daily";
    if (n === 7) return "Weekly";
    if (n === 14) return "Every 2 weeks";
    if (n === 30) return "Monthly";
    if (n === 90) return "Quarterly";
    if (n === 180) return "Every 6 months";
    if (n === 365) return "Yearly";
    if (n === 730) return "Every 2 years";
    return `Every ${n} days`;
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
}

export function createChoreStore() {
  const chores = $state<Chore[]>([]);
  const assignments = $state<Assignment[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/chores");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: ChoreDocument = await resp.json();
      chores.length = 0;
      for (const c of doc.chores) chores.push(c);
      assignments.length = 0;
      for (const a of doc.assignments) assignments.push(a);
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

  async function createChore(data: Omit<Chore, "id">): Promise<void> {
    const resp = await fetch("/api/chores", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateChore(id: string, patch: Partial<Omit<Chore, "id" | "donetickId">>): Promise<void> {
    const resp = await fetch(`/api/chores/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteChore(id: string): Promise<void> {
    const resp = await fetch(`/api/chores/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function completeChore(id: string): Promise<void> {
    const resp = await fetch(`/api/chores/${id}/complete`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function importFromDonetick(token: string): Promise<number> {
    const resp = await fetch("/api/chores/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const { imported } = await resp.json();
    await init();
    return imported as number;
  }

  async function completeAssignment(id: string): Promise<void> {
    const resp = await fetch(`/api/assignments/${id}/complete`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function createAssignment(data: Omit<Assignment, "id">): Promise<void> {
    const resp = await fetch("/api/assignments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateAssignmentPosition(id: string, position: Position): Promise<void> {
    const resp = await fetch(`/api/assignments/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteAssignment(id: string): Promise<void> {
    const resp = await fetch(`/api/assignments/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get chores() { return chores as Chore[]; },
    get assignments() { return assignments as Assignment[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    getProgress,
    getColor,
    assignmentsForRoom,
    houseAssignments,
    createChore,
    updateChore,
    deleteChore,
    completeChore,
    importFromDonetick,
    createAssignment,
    completeAssignment,
    updateAssignmentPosition,
    deleteAssignment,
  };
}
