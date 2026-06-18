export interface Chore {
  id: string;
  donetickId: number | null;
  name: string;
  emoji: string;
  periodDays: number;
  nextDueDate: string;
  description: string;
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

  function getProgress(chore: Chore): number {
    const now = Date.now();
    const due = new Date(chore.nextDueDate).getTime();
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
    updateAssignmentPosition,
    deleteAssignment,
  };
}
