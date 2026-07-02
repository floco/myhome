export interface ConsumablePlacement {
  floorId: string;
  roomId: string | null;
  position: { x: number; y: number };
}

export interface Consumable {
  id: string;
  name: string;
  emoji: string;
  unit: string;
  quantity: number;
  minQuantity: number;
  categoryId: string | null;
  description: string;
  placement: ConsumablePlacement | null;
}

export interface ConsumableTransaction {
  id: string;
  consumableId: string;
  delta: number;
  quantityAfter: number;
  note: string;
  timestamp: string;
}

export interface ConsumableDocument {
  version: number;
  consumables: Consumable[];
  transactions: ConsumableTransaction[];
}

export type StockState = "ok" | "low" | "empty";

export function stockStatus(c: Consumable): StockState {
  if (c.quantity === 0) return "empty";
  if (c.quantity <= c.minQuantity) return "low";
  return "ok";
}

export function barFill(c: Consumable): number {
  if (c.minQuantity === 0) return c.quantity > 0 ? 1 : 0;
  return Math.min(1, c.quantity / (c.minQuantity * 3));
}

export function createConsumableStore() {
  const consumables = $state<Consumable[]>([]);
  const transactions = $state<ConsumableTransaction[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/consumables");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: ConsumableDocument = await resp.json();
      consumables.length = 0;
      for (const c of doc.consumables) consumables.push(c);
      transactions.length = 0;
      for (const t of doc.transactions) transactions.push(t);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createConsumable(
    data: Omit<Consumable, "id" | "placement">,
  ): Promise<void> {
    const resp = await fetch("/api/consumables", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateConsumable(
    id: string,
    patch: Partial<Omit<Consumable, "id" | "placement">>,
  ): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteConsumable(id: string): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function setPlacement(
    id: string,
    placement: ConsumablePlacement | null,
  ): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}/placement`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ placement }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateStock(
    id: string,
    quantity: number,
    note: string = "",
  ): Promise<void> {
    const resp = await fetch(`/api/consumables/${id}/stock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity, note }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteTransaction(id: string): Promise<void> {
    const resp = await fetch(`/api/consumable-transactions/${id}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  function transactionsFor(consumableId: string): ConsumableTransaction[] {
    return transactions.filter((t) => t.consumableId === consumableId);
  }

  function placedConsumables(): Consumable[] {
    return consumables.filter((c) => c.placement !== null);
  }

  init();

  return {
    get consumables() {
      return consumables as Consumable[];
    },
    get transactions() {
      return transactions as ConsumableTransaction[];
    },
    get loaded() {
      return loaded;
    },
    get loadError() {
      return loadError;
    },
    createConsumable,
    updateConsumable,
    deleteConsumable,
    setPlacement,
    updateStock,
    deleteTransaction,
    transactionsFor,
    placedConsumables,
  };
}
