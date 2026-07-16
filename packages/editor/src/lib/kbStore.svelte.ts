export interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
  attachments: string[];
  parentId: string | null;
  icon: string;
  order: number;
  deletedAt?: string | null;
}

export interface KBDocument {
  version: number;
  entries: KBEntry[];
}

export interface KBTrashDocument {
  entries: KBEntry[];
}

export function createKBStore(getHomeId: () => string | null = () => null) {
  const entries = $state<KBEntry[]>([]);
  const trash = $state<KBEntry[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      loadError = null;
      const resp = await fetch(`/api/homes/${homeId}/kb`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: KBDocument = await resp.json();
      entries.length = 0;
      for (const e of doc.entries) entries.push({ attachments: [], parentId: null, icon: "📄", order: 0, ...e });
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createEntry(
    data: { title: string; content: string; parentId?: string | null; icon?: string },
  ): Promise<KBEntry> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const payload: Record<string, unknown> = { title: data.title, content: data.content };
    if (data.parentId !== undefined) payload.parentId = data.parentId;
    if (data.icon !== undefined) payload.icon = data.icon;
    const resp = await fetch(`/api/homes/${homeId}/kb`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const entry: KBEntry = await resp.json();
    await init();
    return entry;
  }

  async function updateEntry(
    id: string,
    patch: { title?: string; content?: string; parentId?: string | null; icon?: string },
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function reorderSiblings(parentId: string | null, orderedIds: string[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/reorder`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parentId, orderedIds }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteEntry(id: string): Promise<number> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.deletedCount as number;
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}/attachments`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(id: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}/attachments/${filename}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function loadTrash(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) return;
    const resp = await fetch(`/api/homes/${homeId}/kb/trash`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const doc: KBTrashDocument = await resp.json();
    trash.length = 0;
    for (const e of doc.entries) trash.push(e);
  }

  async function restoreEntry(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/trash/${id}/restore`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
    await loadTrash();
  }

  async function permanentlyDeleteEntry(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/trash/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await loadTrash();
  }

  async function emptyTrash(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/trash/empty`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await loadTrash();
  }

  init();

  return {
    get entries() { return entries as KBEntry[]; },
    get trash() { return trash as KBEntry[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createEntry,
    updateEntry,
    reorderSiblings,
    deleteEntry,
    uploadAttachment,
    deleteAttachment,
    loadTrash,
    restoreEntry,
    permanentlyDeleteEntry,
    emptyTrash,
    reload: init,
  };
}
