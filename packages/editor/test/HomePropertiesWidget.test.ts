import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import HomePropertiesWidget from "../src/lib/components/HomePropertiesWidget.svelte";
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

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("HomePropertiesWidget", () => {
  it("renders nothing when there are no properties", () => {
    const store = { properties: [] };
    const el = target();
    const comp = mount(HomePropertiesWidget, { target: el, props: { propertiesStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".widget")).toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows status counts and the most recently added properties", () => {
    const store = {
      properties: [
        makeProperty({ id: "p1", name: "Casa Sul", status: "watching", price: 250000 }),
        makeProperty({ id: "p2", name: "Terreno Norte", status: "purchased", price: 90000 }),
      ],
    };
    const el = target();
    const comp = mount(HomePropertiesWidget, { target: el, props: { propertiesStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".widget")).not.toBeNull();
    expect(el.textContent).toContain("Terreno Norte");
    expect(el.textContent).toContain("Casa Sul");
    unmount(comp);
    el.remove();
  });

  it("calls onnavigate when clicked", () => {
    const store = { properties: [makeProperty()] };
    const el = target();
    const onnavigate = vi.fn();
    const comp = mount(HomePropertiesWidget, { target: el, props: { propertiesStore: store, onnavigate } });
    flushSync();
    (el.querySelector(".widget") as HTMLElement).click();
    expect(onnavigate).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});
