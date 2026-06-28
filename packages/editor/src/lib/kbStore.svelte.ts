export interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

export interface KBDocument {
  version: number;
  entries: KBEntry[];
}

export function createKBStore() {
  const entries = $state<KBEntry[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/kb");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: KBDocument = await resp.json();
      entries.length = 0;
      for (const e of doc.entries) entries.push(e);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createEntry(data: { title: string; content: string }): Promise<KBEntry> {
    const resp = await fetch("/api/kb", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const entry: KBEntry = await resp.json();
    await init();
    return entry;
  }

  async function updateEntry(
    id: string,
    patch: { title?: string; content?: string },
  ): Promise<void> {
    const resp = await fetch(`/api/kb/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteEntry(id: string): Promise<void> {
    const resp = await fetch(`/api/kb/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get entries() { return entries as KBEntry[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createEntry,
    updateEntry,
    deleteEntry,
  };
}
