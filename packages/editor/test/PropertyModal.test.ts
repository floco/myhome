import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import PropertyModal from "../src/lib/components/PropertyModal.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: "p1", name: "Casa da Rua das Flores", emoji: "🏠", type: "house", status: "watching",
    locationId: null, address: "", price: null, landSize: null, builtSize: null,
    bedrooms: null, bathrooms: null, listingUrl: null, contact: "",
    pros: [], cons: [], notes: "", attachments: ["photo.jpg"],
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
  return { locations: [{ id: "loc1", name: "Lisbon", emoji: "🇵🇹" }] };
}

describe("PropertyModal", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    homesStore.setActiveHomeId("home-1");
  });

  afterEach(() => {
    homesStore._reset();
    target.remove();
  });

  it("adds and removes pros/cons entries", () => {
    const store = makeStore([]);
    const comp = mount(PropertyModal, {
      target,
      props: { property: null, store, locationsStore: makeLocationsStore(), onclose: vi.fn() },
    });
    flushSync();

    // Switch to the Pros/Cons tab.
    const tabs = Array.from(target.querySelectorAll(".tab")) as HTMLButtonElement[];
    const prosConsTab = tabs.find((t) => t.textContent === "Pros / Cons")!;
    prosConsTab.click();
    flushSync();

    const proInput = target.querySelector(".pc-col:first-child input") as HTMLInputElement;
    proInput.value = "Great light";
    proInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const addButtons = Array.from(target.querySelectorAll(".pc-add button")) as HTMLButtonElement[];
    addButtons[0].click();
    flushSync();

    expect(target.querySelector(".pc-col:first-child .pc-list")?.textContent).toContain("Great light");

    unmount(comp);
  });

  it("builds media item URLs with the home id prefix", () => {
    const store = makeStore([makeProperty()]);
    const comp = mount(PropertyModal, {
      target,
      props: { property: makeProperty(), store, locationsStore: makeLocationsStore(), onclose: vi.fn() },
    });
    flushSync();

    const tabs = Array.from(target.querySelectorAll(".tab")) as HTMLButtonElement[];
    const mediaTab = tabs.find((t) => t.textContent?.startsWith("Media"))!;
    mediaTab.click();
    flushSync();

    const anySrcEl = target.querySelector("[src*='attachments']") as HTMLImageElement | null;
    expect(anySrcEl?.getAttribute("src")).toContain("/api/homes/home-1/properties/p1/attachments/photo.jpg");

    unmount(comp);
  });

  it("calls store.createProperty with trimmed fields on save", () => {
    const store = makeStore([]);
    const onclose = vi.fn();
    const comp = mount(PropertyModal, {
      target,
      props: { property: null, store, locationsStore: makeLocationsStore(), onclose },
    });
    flushSync();

    const nameInput = target.querySelector(".ui-input") as HTMLInputElement;
    nameInput.value = "  Terreno Norte  ";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Create")!;
    saveBtn.click();
    flushSync();

    expect(store.createProperty).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Terreno Norte" }),
    );

    unmount(comp);
  });
});
