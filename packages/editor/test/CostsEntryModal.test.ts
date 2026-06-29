import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CostsEntryModal from "../src/lib/components/CostsEntryModal.svelte";
import type { CostEntry } from "../src/lib/costsStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeEntry(overrides: Partial<CostEntry> = {}): CostEntry {
  return {
    id: "c1", categoryId: "cat-electricity", date: "2026-01-15",
    totalAmount: 120.5, quantity: null, unitPrice: null,
    supplierId: null, notes: "", roomId: null, attachments: [], ...overrides,
  };
}

function makeSettingsStore() {
  return {
    costCategories: [{ id: "cat-electricity", name: "Electricity", emoji: "⚡", color: "#ff0", unit: null }],
    suppliers: [],
    workCategories: [],
  };
}

function makeFloorStore() {
  return { floors: [] };
}

function makeCostsStore(entries: CostEntry[] = []) {
  return {
    entries,
    loaded: true,
    loadError: null,
    createEntry: vi.fn().mockResolvedValue(undefined),
    updateEntry: vi.fn().mockResolvedValue(undefined),
    deleteEntry: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("receipt.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    totalByYear: vi.fn().mockReturnValue(new Map()),
    breakdownLastCompleteYear: vi.fn().mockReturnValue([]),
    entriesByYear: vi.fn().mockReturnValue(new Map()),
    lastCompleteYear: vi.fn().mockReturnValue(2025),
  };
}

describe("CostsEntryModal — Media tab", () => {
  it("shows Info and Media tabs when editing", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry();
    const costsStore = makeCostsStore([entry]);
    const app = mount(CostsEntryModal, {
      target,
      props: { entry, costsStore, settingsStore: makeSettingsStore(), floorStore: makeFloorStore(), onclose: vi.fn() },
    });
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Info");
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    unmount(app);
  });

  it("Media tab is disabled when creating (entry=null)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const costsStore = makeCostsStore();
    const app = mount(CostsEntryModal, {
      target,
      props: { entry: null, costsStore, settingsStore: makeSettingsStore(), floorStore: makeFloorStore(), onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement | undefined;
    expect(mediaTab?.disabled).toBe(true);
    unmount(app);
  });

  it("clicking Media tab renders MediaGallery drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ attachments: ["receipt.jpg"] });
    const costsStore = makeCostsStore([entry]);
    const app = mount(CostsEntryModal, {
      target,
      props: { entry, costsStore, settingsStore: makeSettingsStore(), floorStore: makeFloorStore(), onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
  });
});
