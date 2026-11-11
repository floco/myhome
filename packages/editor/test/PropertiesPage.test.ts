import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import PropertiesPage from "../src/lib/components/PropertiesPage.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";
import { fake } from "./fixtures/fake";

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: "p1", name: "Casa da Rua das Flores", emoji: "🏠", type: "house", status: "watching",
    locationId: null, address: "", price: null, landSize: null, builtSize: null,
    bedrooms: null, bathrooms: null, listingUrl: null, contact: "",
    pros: [], cons: [], notes: "", attachments: [],
    ...overrides,
  };
}

function makeStore(properties: Property[]) {
  return {
    properties, loaded: true, loadError: null,
    createProperty: vi.fn(), updateProperty: vi.fn(), deleteProperty: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(), reload: vi.fn(),
  };
}

function makeLocationsStore() {
  return { locations: [] };
}

describe("PropertiesPage — external selection", () => {
  it("opens the edit modal for the property matching selectedItemId and clears selection", () => {
    const store = makeStore([makeProperty()]);
    const onclearselection = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(PropertiesPage, {
      target,
      props: { store, locationsStore: fake(makeLocationsStore()), selectedItemId: "p1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit property");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });
});

describe("PropertiesPage — filters", () => {
  it("filters the table by status", () => {
    const store = makeStore([
      makeProperty({ id: "p1", name: "Casa Sul", status: "watching" }),
      makeProperty({ id: "p2", name: "Casa Norte", status: "purchased" }),
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: fake(makeLocationsStore()) } });
    flushSync();

    (target.querySelector('button[aria-label="Filters"]') as HTMLButtonElement).click();
    flushSync();

    const statusSelect = target.querySelectorAll("select.filter-sel")[0] as HTMLSelectElement;
    statusSelect.value = "purchased";
    statusSelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    expect(target.textContent).toContain("Casa Norte");
    expect(target.textContent).not.toContain("Casa Sul");

    unmount(comp);
  });
});

describe("PropertiesPage — add property", () => {
  it("opens the create modal when the add button is clicked", () => {
    const store = makeStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: fake(makeLocationsStore()) } });
    flushSync();

    const addBtn = target.querySelector('button[title="Add property"]') as HTMLButtonElement;
    addBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("＋ New property");

    unmount(comp);
  });
});

describe("PropertiesPage — responsive columns", () => {
  it("hides type/size at tablet and location/price at mobile", () => {
    const store = makeStore([makeProperty()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: fake(makeLocationsStore()) } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, type, location, price, size, status
    expect(headers[2].classList.contains("col-hide-tablet")).toBe(true); // type
    expect(headers[5].classList.contains("col-hide-tablet")).toBe(true); // size
    expect(headers[3].classList.contains("col-hide-mobile")).toBe(true); // location
    expect(headers[4].classList.contains("col-hide-mobile")).toBe(true); // price
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(false); // name

    unmount(comp);
  });
});

describe("PropertiesPage — suggestions tab", () => {
  function makeSearchStore(newCount: number) {
    return {
      searches: [], suggestions: [], loaded: true, loadError: null, newCount,
      accept: vi.fn(), reject: vi.fn(), togglePin: vi.fn(), reload: vi.fn().mockResolvedValue(undefined),
    };
  }

  function mountWith(searchStore: ReturnType<typeof makeSearchStore>) {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PropertiesPage, {
      target,
      props: { store: makeStore([makeProperty()]), locationsStore: makeLocationsStore(), searchStore } as any,
    });
    flushSync();
    return { target, comp };
  }

  it("reloads the inbox when the suggestions tab is opened", () => {
    const searchStore = makeSearchStore(0);
    const { target, comp } = mountWith(searchStore);
    searchStore.reload.mockClear();
    (target.querySelectorAll(".tab-bar .tab")[1] as HTMLButtonElement).click();
    flushSync();
    expect(searchStore.reload).toHaveBeenCalledTimes(1);
    unmount(comp);
  });

  it("polls the inbox every 60s while visible and stops after unmount", () => {
    vi.useFakeTimers();
    try {
      const searchStore = makeSearchStore(0);
      const { comp } = mountWith(searchStore);
      searchStore.reload.mockClear();
      vi.advanceTimersByTime(60_000);
      expect(searchStore.reload).toHaveBeenCalledTimes(1);
      Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
      vi.advanceTimersByTime(60_000);
      expect(searchStore.reload).toHaveBeenCalledTimes(1);
      Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
      unmount(comp);
      vi.advanceTimersByTime(120_000);
      expect(searchStore.reload).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("reloads the inbox when the page becomes visible again", () => {
    const searchStore = makeSearchStore(0);
    const { comp } = mountWith(searchStore);
    searchStore.reload.mockClear();
    document.dispatchEvent(new Event("visibilitychange"));
    expect(searchStore.reload).toHaveBeenCalledTimes(1);
    unmount(comp);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(searchStore.reload).toHaveBeenCalledTimes(1);
  });

  it("shows suggestions badge count and switches tab", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PropertiesPage, {
      target,
      props: { store: makeStore([makeProperty()]), locationsStore: makeLocationsStore(), searchStore: makeSearchStore(3) } as any,
    });
    flushSync();
    const tabs = [...target.querySelectorAll(".tab-bar .tab")].map((t) => t.textContent);
    expect(tabs).toEqual(["Properties", "Suggestions (3)"]);
    (target.querySelectorAll(".tab-bar .tab")[1] as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector("thead")).toBeNull();
    expect(target.textContent).toContain("No search defined yet");
    unmount(comp);
  });

  it("has no tabs without a search store", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(PropertiesPage, { target, props: { store: makeStore([]), locationsStore: fake(makeLocationsStore()) } });
    flushSync();
    expect(target.querySelector(".tab-bar")).toBeNull();
    unmount(comp);
  });
});
