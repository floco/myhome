import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CostsEntryModal from "../src/lib/components/CostsEntryModal.svelte";
import type { CostEntry } from "../src/lib/costsStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeEntry(overrides: Partial<CostEntry> = {}): CostEntry {
  return {
    id: "c1", categoryId: "cat-electricity", date: "2026-01-15",
    totalAmount: 120.5, quantity: null, unitPrice: null,
    contactId: null, notes: "", roomId: null, attachments: [], ...overrides,
  };
}

function makeSettingsStore() {
  return {
    costCategories: [{ id: "cat-electricity", name: "Electricity", emoji: "⚡", color: "#ff0", unit: null }],
    workCategories: [],
  };
}

function makeContactsStore() {
  return { contacts: [] };
}

function makeFloorStore() {
  return { floors: [] };
}

function makeConsumableStore() {
  return { consumables: [] };
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

describe("CostsEntryModal — notes links", () => {
  it("renders a URL in notes as a clickable link when not editing", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ notes: "Invoice: https://example.com/invoice.pdf" });
    const costsStore = makeCostsStore([entry]);
    const app = mount(CostsEntryModal, {
      target,
      props: { entry, costsStore, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), floorStore: makeFloorStore(), consumableStore: makeConsumableStore(), onclose: vi.fn() },
    });
    flushSync();
    const link = target.querySelector(".md-preview a") as HTMLAnchorElement | null;
    expect(link?.getAttribute("href")).toBe("https://example.com/invoice.pdf");
    unmount(app);
  });
});

describe("CostsEntryModal — Media tab", () => {
  it("shows Info and Media tabs when editing", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry();
    const costsStore = makeCostsStore([entry]);
    const app = mount(CostsEntryModal, {
      target,
      props: { entry, costsStore, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), floorStore: makeFloorStore(), consumableStore: makeConsumableStore(), onclose: vi.fn() },
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
      props: { entry: null, costsStore, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), floorStore: makeFloorStore(), consumableStore: makeConsumableStore(), onclose: vi.fn() },
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
      props: { entry, costsStore, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), floorStore: makeFloorStore(), consumableStore: makeConsumableStore(), onclose: vi.fn() },
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

describe("CostsEntryModal — link to stock", () => {
  function makeConsumableStoreWithItems() {
    return { consumables: [{ id: "con1", name: "Heating Oil", emoji: "🛢️", unit: "L" }] };
  }

  it("shows the stock-impact hint once a consumable and quantity are set, and saves the link", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const costsStore = makeCostsStore();
    const app = mount(CostsEntryModal, {
      target,
      props: {
        entry: null, costsStore,
        settingsStore: { costCategories: [{ id: "cat-fuel", name: "Fuel", emoji: "🛢", color: "#46c", unit: "L" }], workCategories: [] },
        contactsStore: makeContactsStore(), floorStore: makeFloorStore(),
        consumableStore: makeConsumableStoreWithItems(), onclose: vi.fn(),
      },
    });
    flushSync();

    const quantityInput = target.querySelector('input[type="number"]') as HTMLInputElement;
    quantityInput.value = "1000";
    quantityInput.dispatchEvent(new Event("input", { bubbles: true }));
    const linkSelect = Array.from(target.querySelectorAll("select")).find(s =>
      Array.from(s.options).some(o => o.textContent?.includes("Heating Oil")),
    ) as HTMLSelectElement;
    linkSelect.value = "con1";
    linkSelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    expect(target.textContent).toContain("Heating Oil");

    const totalInput = Array.from(target.querySelectorAll('input[type="number"]'))
      .find(i => (i as HTMLInputElement).placeholder === "0.00") as HTMLInputElement;
    totalInput.value = "900";
    totalInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find(b => b.textContent?.trim() === "Create") as HTMLButtonElement;
    saveBtn.click();
    flushSync();

    expect(costsStore.createEntry).toHaveBeenCalledWith(
      expect.objectContaining({ linkedConsumableId: "con1", quantity: 1000 }),
    );
    unmount(app);
  });

  it("does not render the link section when there are no consumables", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const costsStore = makeCostsStore();
    const app = mount(CostsEntryModal, {
      target,
      props: {
        entry: null, costsStore, settingsStore: makeSettingsStore(),
        contactsStore: makeContactsStore(), floorStore: makeFloorStore(),
        consumableStore: makeConsumableStore(), onclose: vi.fn(),
      },
    });
    flushSync();
    expect(target.textContent).not.toContain("Link to stock item");
    unmount(app);
  });
});
