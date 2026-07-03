export interface InventoryPosition {
  x: number;
  y: number;
}

export interface InventoryPlacement {
  floorId: string;
  roomId: string | null;
  position: InventoryPosition;
}

export interface InventoryItem {
  id: string;
  name: string;
  emoji: string;
  category: string;
  brand: string | null;
  model: string | null;
  serialNumber: string | null;
  purchaseDate: string | null;
  purchasePrice: number | null;
  warrantyExpiryDate: string | null;
  notes: string;
  attachments: string[];
  placement: InventoryPlacement | null;
}

export type WarrantyStatus = "ok" | "soon" | "expired";

export function createInventoryStore(getHomeId: () => string | null = () => null) {
  const items = $state<InventoryItem[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/inventory`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: { items: InventoryItem[] } = await resp.json();
      items.length = 0;
      for (const i of doc.items) items.push(i);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  function warrantyStatus(item: InventoryItem): WarrantyStatus {
    if (!item.warrantyExpiryDate) return "ok";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    if (expiry < now) return "expired";
    if (expiry - now <= 30 * 86400 * 1000) return "soon";
    return "ok";
  }

  function placedItems(): InventoryItem[] {
    return items.filter((i) => i.placement !== null);
  }

  function unplacedItems(): InventoryItem[] {
    return items.filter((i) => i.placement === null);
  }

  async function createItem(
    data: Omit<InventoryItem, "id" | "attachments" | "placement">
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/inventory/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateItem(
    id: string,
    patch: Partial<Omit<InventoryItem, "id" | "attachments" | "placement">>
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/inventory/items/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteItem(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/inventory/items/${id}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function setPlacement(
    id: string,
    placement: InventoryPlacement | null
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/inventory/items/${id}/placement`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ placement }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/inventory/items/${id}/attachments`, {
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
    const resp = await fetch(`/api/homes/${homeId}/inventory/items/${id}/attachments/${filename}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get items() { return items as InventoryItem[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    warrantyStatus,
    placedItems,
    unplacedItems,
    createItem,
    updateItem,
    deleteItem,
    setPlacement,
    uploadAttachment,
    deleteAttachment,
    reload: init,
  };
}
