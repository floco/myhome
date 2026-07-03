// packages/editor/src/lib/costsStore.svelte.ts
import type { CostCategory } from "./settingsStore.svelte";

export interface CostEntry {
  id: string;
  categoryId: string;
  date: string;
  totalAmount: number;
  quantity: number | null;
  unitPrice: number | null;
  supplierId: string | null;
  notes: string;
  roomId: string | null;
  attachments: string[];
}

export interface CostsDocument {
  version: number;
  entries: CostEntry[];
}

export interface CategoryBreakdown {
  categoryId: string;
  name: string;
  emoji: string;
  color: string;
  unit: string | null;
  totalAmount: number;
  pct: number;
}

export interface YearData {
  totalAmount: number;
  totalQuantity: number | null;
}

export function createCostsStore(getHomeId: () => string | null = () => null) {
  const entries = $state<CostEntry[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/costs`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: CostsDocument = await resp.json();
      entries.length = 0;
      for (const e of doc.entries) entries.push(e);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createEntry(data: Omit<CostEntry, "id" | "attachments">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/costs/entries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateEntry(
    id: string,
    patch: Partial<Omit<CostEntry, "id">>
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/costs/entries/${id}`, {
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
    const resp = await fetch(`/api/homes/${homeId}/costs/entries/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/costs/entries/${id}/attachments`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(id: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/costs/entries/${id}/attachments/${filename}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  function lastCompleteYear(): number {
    const currentYear = new Date().getFullYear();
    const years = [...new Set(entries.map(e => new Date(e.date).getFullYear()))].sort();
    if (years.length === 0) return currentYear - 1;
    const complete = years.filter(y => y < currentYear);
    return complete.length > 0 ? complete[complete.length - 1] : years[years.length - 1];
  }

  function totalByYear(): Map<number, number> {
    const map = new Map<number, number>();
    for (const e of entries) {
      const y = new Date(e.date).getFullYear();
      map.set(y, (map.get(y) ?? 0) + e.totalAmount);
    }
    return map;
  }

  function breakdownLastCompleteYear(categories: CostCategory[]): CategoryBreakdown[] {
    const year = lastCompleteYear();
    const yearEntries = entries.filter(e => new Date(e.date).getFullYear() === year);
    const totals = new Map<string, number>();
    for (const e of yearEntries) {
      totals.set(e.categoryId, (totals.get(e.categoryId) ?? 0) + e.totalAmount);
    }
    const grandTotal = [...totals.values()].reduce((a, b) => a + b, 0);
    if (grandTotal === 0) return [];
    return [...totals.entries()]
      .map(([categoryId, totalAmount]) => {
        const cat = categories.find(c => c.id === categoryId);
        return {
          categoryId,
          name: cat?.name ?? "Unknown",
          emoji: cat?.emoji ?? "?",
          color: cat?.color ?? "#667",
          unit: cat?.unit ?? null,
          totalAmount,
          pct: (totalAmount / grandTotal) * 100,
        };
      })
      .sort((a, b) => b.totalAmount - a.totalAmount);
  }

  function entriesByYear(categoryId: string): Map<number, YearData> {
    const map = new Map<number, YearData>();
    const catEntries = entries.filter(e => e.categoryId === categoryId);
    for (const e of catEntries) {
      const y = new Date(e.date).getFullYear();
      const prev = map.get(y) ?? { totalAmount: 0, totalQuantity: null };
      const newQty = e.quantity != null
        ? (prev.totalQuantity ?? 0) + e.quantity
        : prev.totalQuantity;
      map.set(y, {
        totalAmount: prev.totalAmount + e.totalAmount,
        totalQuantity: newQty,
      });
    }
    return map;
  }

  init();

  return {
    get entries() { return entries as CostEntry[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createEntry,
    updateEntry,
    deleteEntry,
    uploadAttachment,
    deleteAttachment,
    totalByYear,
    breakdownLastCompleteYear,
    entriesByYear,
    lastCompleteYear,
    reload: init,
  };
}
