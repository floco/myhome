// packages/editor/src/lib/worksStore.svelte.ts

export interface WorkPosition {
  x: number;
  y: number;
}

export interface WorkPlacement {
  floorId: string;
  position: WorkPosition;
}

export interface Work {
  id: string;
  title: string;
  description: string;
  status: "planned" | "in_progress" | "done";
  categoryId: string | null;
  date: string;
  totalCost: number | null;
  supplierId: string | null;
  notes: string;
  attachments: string[];
  placement: WorkPlacement | null;
}

export interface WorksDocument {
  version: number;
  works: Work[];
}

export function createWorksStore(getHomeId: () => string | null = () => null) {
  const works = $state<Work[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/works`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: WorksDocument = await resp.json();
      works.length = 0;
      for (const w of doc.works) works.push(w);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createWork(
    data: Omit<Work, "id" | "attachments" | "placement">
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/works`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateWork(
    id: string,
    patch: Partial<Omit<Work, "id" | "attachments" | "placement">>
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/works/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteWork(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/works/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/works/${id}/attachments`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(id: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/works/${id}/attachments/${filename}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function setPlacement(
    id: string,
    placement: WorkPlacement | null
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    if (placement === null) {
      const resp = await fetch(`/api/homes/${homeId}/works/${id}/placement`, { method: "DELETE" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    } else {
      const resp = await fetch(`/api/homes/${homeId}/works/${id}/placement`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(placement),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    }
    await init();
  }

  init();

  return {
    get works() { return works as Work[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createWork,
    updateWork,
    deleteWork,
    uploadAttachment,
    deleteAttachment,
    setPlacement,
    reload: init,
  };
}
