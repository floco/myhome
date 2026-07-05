import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CostsPage from "../src/lib/components/CostsPage.svelte";
import type { CostEntry } from "../src/lib/costsStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeEntry(overrides: Partial<CostEntry> = {}): CostEntry {
  return {
    id: "ce1", categoryId: "cat-electricity", date: "2026-01-15",
    totalAmount: 120.5, quantity: null, unitPrice: null,
    supplierId: null, notes: "", roomId: null, attachments: [],
    ...overrides,
  };
}

function makeCostsStore(entries: CostEntry[]) {
  return {
    entries, loaded: true, loadError: null,
    createEntry: vi.fn(), updateEntry: vi.fn(), deleteEntry: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(),
    totalByYear: vi.fn().mockReturnValue(new Map()),
    breakdownLastCompleteYear: vi.fn().mockReturnValue([]),
    entriesByYear: vi.fn().mockReturnValue(new Map()),
    lastCompleteYear: vi.fn().mockReturnValue(2025),
  };
}

function makeSettingsStore() {
  return {
    costCategories: [{ id: "cat-electricity", name: "Electricity", emoji: "💡", color: "#ff0", unit: null }],
    suppliers: [],
    workCategories: [],
  };
}

describe("CostsPage — external selection", () => {
  it("opens the edit modal for the entry matching selectedItemId and clears selection", () => {
    const entry = makeEntry();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const onclearselection = vi.fn();
    const comp = mount(CostsPage, {
      target,
      props: {
        costsStore: makeCostsStore([entry]),
        settingsStore: makeSettingsStore(),
        floorStore: { floors: [] },
        selectedItemId: "ce1",
        onclearselection,
      },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit entry");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });
});
