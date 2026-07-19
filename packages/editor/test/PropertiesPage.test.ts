import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import PropertiesPage from "../src/lib/components/PropertiesPage.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";

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
      props: { store, locationsStore: makeLocationsStore(), selectedItemId: "p1", onclearselection },
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

    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: makeLocationsStore() } });
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

    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: makeLocationsStore() } });
    flushSync();

    const addBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Add property"))!;
    addBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("＋ New property");

    unmount(comp);
  });
});
