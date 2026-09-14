import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount } from "svelte";
import ConsumableOverlay from "../src/lib/components/ConsumableOverlay.svelte";
import type { Consumable } from "../src/lib/consumableStore.svelte";

afterEach(() => vi.unstubAllGlobals());

function makeConsumable(overrides: Partial<Consumable> = {}): Consumable {
  return {
    id: "c1", name: "Dish Soap", emoji: "🧴", unit: "mL", quantity: 5,
    minQuantity: 2, categoryId: null, description: "",
    placement: { floorId: "f1", roomId: null, position: { x: 1, y: 2 } },
    ...overrides,
  };
}

describe("ConsumableOverlay", () => {
  it("renders one badge per placed consumable", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ConsumableOverlay, {
      target,
      props: {
        consumables: [makeConsumable({ id: "c1" }), makeConsumable({ id: "c2" })],
        viewport: { panX: 0, panY: 0, zoom: 100 },
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    expect(target.querySelectorAll("svg g").length).toBe(2);

    unmount(comp);
    target.remove();
  });

  it("scales the badge group at 2x the base zoom-derived scale", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    // zoom 80 -> base scale would be 1.0, so the badge should render at scale(2)
    const comp = mount(ConsumableOverlay, {
      target,
      props: {
        consumables: [makeConsumable()],
        viewport: { panX: 0, panY: 0, zoom: 80 },
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const g = target.querySelector("svg g");
    expect(g?.getAttribute("transform")).toContain("scale(2)");

    unmount(comp);
    target.remove();
  });

  it("does not render a badge for unplaced consumables", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(ConsumableOverlay, {
      target,
      props: {
        consumables: [makeConsumable({ placement: null })],
        viewport: { panX: 0, panY: 0, zoom: 100 },
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    expect(target.querySelectorAll("svg g").length).toBe(0);

    unmount(comp);
    target.remove();
  });
});
