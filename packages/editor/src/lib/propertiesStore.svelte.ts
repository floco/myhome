// packages/editor/src/lib/propertiesStore.svelte.ts

export type PropertyType = "land" | "house" | "new_build";
export type PropertyStatus = "watching" | "visited" | "proposal_made" | "purchased" | "rejected";

export interface Property {
  id: string;
  name: string;
  emoji: string;
  type: PropertyType;
  status: PropertyStatus;
  locationId: string | null;
  address: string;
  price: number | null;
  landSize: number | null;
  builtSize: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  listingUrl: string | null;
  contact: string;
  pros: string[];
  cons: string[];
  notes: string;
  attachments: string[];
}

export interface PropertiesDocument {
  version: number;
  properties: Property[];
}

export function createPropertiesStore(getHomeId: () => string | null = () => null) {
  const properties = $state<Property[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/properties`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: PropertiesDocument = await resp.json();
      properties.length = 0;
      for (const p of doc.properties) properties.push(p);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createProperty(
    data: Omit<Property, "id" | "attachments">
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/properties`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateProperty(
    id: string,
    patch: Partial<Omit<Property, "id" | "attachments">>
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteProperty(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}/attachments`, {
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
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}/attachments/${filename}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get properties() { return properties as Property[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createProperty,
    updateProperty,
    deleteProperty,
    uploadAttachment,
    deleteAttachment,
    reload: init,
  };
}
