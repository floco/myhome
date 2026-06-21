// packages/editor/src/lib/settingsStore.svelte.ts

export interface CostCategoryPosition {
  x: number;
  y: number;
}

export interface CostCategoryPlacement {
  floorId: string;
  position: CostCategoryPosition;
}

export interface CostCategory {
  id: string;
  name: string;
  emoji: string;
  unit: string | null;
  color: string;
  placement?: CostCategoryPlacement | null;
}

export interface InventoryCategory {
  id: string;
  name: string;
}

export interface SettingsDocument {
  version: number;
  costCategories: CostCategory[];
  inventoryCategories: InventoryCategory[];
}

export function createSettingsStore() {
  const costCategories = $state<CostCategory[]>([]);
  const inventoryCategories = $state<InventoryCategory[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/settings");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: SettingsDocument = await resp.json();
      costCategories.length = 0;
      for (const c of doc.costCategories) costCategories.push(c);
      inventoryCategories.length = 0;
      for (const c of doc.inventoryCategories) inventoryCategories.push(c);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function updateCostCategories(list: CostCategory[]): Promise<void> {
    const resp = await fetch("/api/settings/cost-categories", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(list),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateInventoryCategories(list: InventoryCategory[]): Promise<void> {
    const resp = await fetch("/api/settings/inventory-categories", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(list),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function placeCostCategory(id: string, placement: CostCategoryPlacement | null): Promise<void> {
    if (placement === null) {
      const resp = await fetch(`/api/settings/cost-categories/${id}/placement`, { method: "DELETE" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    } else {
      const resp = await fetch(`/api/settings/cost-categories/${id}/placement`, {
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
    get costCategories() { return costCategories as CostCategory[]; },
    get inventoryCategories() { return inventoryCategories as InventoryCategory[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    updateCostCategories,
    updateInventoryCategories,
    placeCostCategory,
  };
}
