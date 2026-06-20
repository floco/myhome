import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount } from "svelte";
import InventoryOverlay from "../src/lib/components/InventoryOverlay.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

afterEach(() => vi.unstubAllGlobals());

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1", name: "TV", emoji: "📺", category: "", brand: null,
    model: null, serialNumber: null, purchaseDate: null,
    purchasePrice: null, warrantyExpiryDate: null, notes: "",
    placement: { floorId: "f1", roomId: null, position: { x: 1, y: 2 } },
    ...overrides,
  };
}

const viewport = { panX: 0, panY: 0, zoom: 100 };

describe("InventoryOverlay", () => {
  it("renders one emoji pin per placed item", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ id: "i1", emoji: "📺" }), makeItem({ id: "i2", emoji: "🧺" })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const emojiTexts = Array.from(target.querySelectorAll("text")).filter(
      (t) => t.textContent === "📺" || t.textContent === "🧺"
    );
    expect(emojiTexts.length).toBe(2);

    unmount(comp);
    target.remove();
  });

  it("renders no pins for unplaced items", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ placement: null })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const svgGroups = target.querySelectorAll("svg g");
    expect(svgGroups.length).toBe(0);

    unmount(comp);
    target.remove();
  });

  it("applies orange drop-shadow for soon-expiring warranty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const soonDate = new Date(Date.now() + 15 * 86400 * 1000)
      .toISOString()
      .slice(0, 10);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ warrantyExpiryDate: soonDate })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const emojiText = Array.from(target.querySelectorAll("text")).find(
      (t) => t.textContent === "📺"
    );
    expect(emojiText?.getAttribute("style")).toContain(
      "drop-shadow(0 0 6px #ff9800)"
    );

    unmount(comp);
    target.remove();
  });

  it("applies red drop-shadow for expired warranty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const pastDate = new Date(Date.now() - 86400 * 1000)
      .toISOString()
      .slice(0, 10);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem({ warrantyExpiryDate: pastDate })],
        viewport,
        active: true,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const emojiText = Array.from(target.querySelectorAll("text")).find(
      (t) => t.textContent === "📺"
    );
    expect(emojiText?.getAttribute("style")).toContain(
      "drop-shadow(0 0 6px #f44336)"
    );

    unmount(comp);
    target.remove();
  });

  it("sets pointer-events none when not active", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem()],
        viewport,
        active: false,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const g = target.querySelector("svg g");
    expect(g?.getAttribute("style")).toContain("pointer-events:none");

    unmount(comp);
    target.remove();
  });
});
