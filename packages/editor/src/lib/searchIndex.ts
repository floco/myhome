import type { Chore } from "./choreStore.svelte";
import type { InventoryItem } from "./inventoryStore.svelte";
import type { Consumable } from "./consumableStore.svelte";
import type { Work } from "./worksStore.svelte";
import type { CostEntry } from "./costsStore.svelte";
import type { KBEntry } from "./kbStore.svelte";
import type { CostCategory, WorkCategory, Supplier } from "./settingsStore.svelte";

export type SearchModule = "chores" | "inventory" | "consumables" | "works" | "costs" | "kb";

export const MODULE_ORDER: SearchModule[] = ["chores", "inventory", "consumables", "works", "costs", "kb"];

export const MODULE_LABELS: Record<SearchModule, string> = {
  chores: "Chores",
  inventory: "Inventory",
  consumables: "Consumables",
  works: "Works",
  costs: "Costs",
  kb: "Knowledge Base",
};

export interface SearchResult {
  module: SearchModule;
  id: string;
  icon: string;
  title: string;
  subtitle: string;
  searchText: string;
  titleText: string;
}

export interface SearchStores {
  choreStore: { chores: Chore[] };
  inventoryStore: { items: InventoryItem[] };
  consumableStore: { consumables: Consumable[] };
  worksStore: { works: Work[] };
  costsStore: { entries: CostEntry[] };
  kbStore: { entries: KBEntry[] };
  settingsStore: { costCategories: CostCategory[]; workCategories: WorkCategory[]; suppliers: Supplier[] };
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function statusLabel(status: Work["status"]): string {
  if (status === "in_progress") return "In progress";
  if (status === "done") return "Done";
  return "Planned";
}

function norm(...parts: (string | null | undefined)[]): string {
  return parts.filter((p): p is string => !!p).join(" ").toLowerCase();
}

export function buildSearchIndex(stores: SearchStores): SearchResult[] {
  const results: SearchResult[] = [];

  for (const chore of stores.choreStore.chores) {
    results.push({
      module: "chores",
      id: chore.id,
      icon: chore.emoji,
      title: chore.name,
      subtitle: fmtDate(chore.nextDueDate),
      searchText: norm(chore.name, chore.description),
      titleText: chore.name.toLowerCase(),
    });
  }

  for (const item of stores.inventoryStore.items) {
    results.push({
      module: "inventory",
      id: item.id,
      icon: item.emoji,
      title: item.name,
      subtitle: item.category || "Inventory",
      searchText: norm(item.name, item.brand, item.model, item.serialNumber, item.notes),
      titleText: item.name.toLowerCase(),
    });
  }

  for (const c of stores.consumableStore.consumables) {
    results.push({
      module: "consumables",
      id: c.id,
      icon: c.emoji,
      title: c.name,
      subtitle: `${c.quantity} ${c.unit}`,
      searchText: norm(c.name, c.description),
      titleText: c.name.toLowerCase(),
    });
  }

  const workCategoryMap = new Map(stores.settingsStore.workCategories.map((c) => [c.id, c]));
  for (const work of stores.worksStore.works) {
    const category = work.categoryId ? workCategoryMap.get(work.categoryId) : undefined;
    results.push({
      module: "works",
      id: work.id,
      icon: category?.emoji ?? "🔧",
      title: work.title,
      subtitle: `${statusLabel(work.status)} · ${fmtDate(work.date)}`,
      searchText: norm(work.title, work.description, work.notes),
      titleText: work.title.toLowerCase(),
    });
  }

  const costCategoryMap = new Map(stores.settingsStore.costCategories.map((c) => [c.id, c]));
  const supplierMap = new Map(stores.settingsStore.suppliers.map((s) => [s.id, s]));
  for (const entry of stores.costsStore.entries) {
    const category = costCategoryMap.get(entry.categoryId);
    const supplier = entry.supplierId ? supplierMap.get(entry.supplierId) : undefined;
    const title = category?.name ?? "Cost entry";
    results.push({
      module: "costs",
      id: entry.id,
      icon: category?.emoji ?? "💶",
      title,
      subtitle: `${entry.totalAmount} €`,
      searchText: norm(title, supplier?.name, entry.notes),
      titleText: title.toLowerCase(),
    });
  }

  for (const entry of stores.kbStore.entries) {
    results.push({
      module: "kb",
      id: entry.id,
      icon: "📄",
      title: entry.title,
      subtitle: "Knowledge Base",
      searchText: norm(entry.title, entry.content),
      titleText: entry.title.toLowerCase(),
    });
  }

  return results;
}

export function filterResults(index: SearchResult[], query: string, limit = 20): SearchResult[] {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];

  const matches = index.filter((r) => r.searchText.includes(q));
  matches.sort((a, b) => {
    const moduleDelta = MODULE_ORDER.indexOf(a.module) - MODULE_ORDER.indexOf(b.module);
    if (moduleDelta !== 0) return moduleDelta;
    const aTitle = a.titleText.includes(q) ? 0 : 1;
    const bTitle = b.titleText.includes(q) ? 0 : 1;
    return aTitle - bTitle;
  });
  return matches.slice(0, limit);
}
