export interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
  attachments: string[];
  folderId: string | null;
}

export interface KBFolder {
  id: string;
  name: string;
  parentId: string | null;
}

export interface KBDocument {
  version: number;
  entries: KBEntry[];
  folders: KBFolder[];
}

export function createKBStore(getHomeId: () => string | null = () => null) {
  const entries = $state<KBEntry[]>([]);
  const folders = $state<KBFolder[]>([]);
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
      for (const e of doc.entries) entries.push({ attachments: [], folderId: null, ...e });
      folders.length = 0;
      for (const f of doc.folders ?? []) folders.push(f);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createEntry(
    data: { title: string; content: string; folderId?: string | null },
  ): Promise<KBEntry> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const payload: Record<string, unknown> = { title: data.title, content: data.content };
    if (data.folderId !== undefined) payload.folderId = data.folderId;
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
    patch: { title?: string; content?: string; folderId?: string | null },
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

  async function deleteEntry(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
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

  async function createFolder(data: { name: string; parentId?: string | null }): Promise<KBFolder> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/folders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: data.name, parentId: data.parentId ?? null }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const folder: KBFolder = await resp.json();
    await init();
    return folder;
  }

  async function updateFolder(
    id: string,
    patch: { name?: string; parentId?: string | null },
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/folders/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteFolder(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/kb/folders/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get entries() { return entries as KBEntry[]; },
    get folders() { return folders as KBFolder[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createEntry,
    updateEntry,
    deleteEntry,
    uploadAttachment,
    deleteAttachment,
    createFolder,
    updateFolder,
    deleteFolder,
    reload: init,
  };
}
