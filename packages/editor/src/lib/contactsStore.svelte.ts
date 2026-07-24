// packages/editor/src/lib/contactsStore.svelte.ts

export interface Contact {
  id: string;
  name: string;
  companyName: string | null;
  typeId: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  website: string | null;
  notes: string;
}

export interface ContactsDocument {
  version: number;
  contacts: Contact[];
}

export interface ContactUsageRef {
  module: string;
  id: string;
  label: string;
}

export function createContactsStore(getHomeId: () => string | null = () => null) {
  const contacts = $state<Contact[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/contacts`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: ContactsDocument = await resp.json();
      contacts.length = 0;
      for (const c of doc.contacts) contacts.push(c);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createContact(data: Omit<Contact, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/contacts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateContact(id: string, patch: Partial<Omit<Contact, "id">>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/contacts/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteContact(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/contacts/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function getUsage(id: string): Promise<ContactUsageRef[]> {
    const homeId = getHomeId();
    if (!homeId) return [];
    const resp = await fetch(`/api/homes/${homeId}/contacts/${id}/usage`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    return data.references as ContactUsageRef[];
  }

  init();

  return {
    get contacts() { return contacts as Contact[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createContact,
    updateContact,
    deleteContact,
    getUsage,
    reload: init,
  };
}
