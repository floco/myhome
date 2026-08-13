import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import { readFileSync } from "node:fs";
import ItemPickerPanel from "../src/lib/components/ItemPickerPanel.svelte";
import type { PickerLayer } from "../src/lib/components/ItemPickerPanel.svelte";

const CHORES_LAYER: PickerLayer = {
  id: "chores", label: "Chores", emoji: "✅",
  items: [
    { id: "c1", name: "Vacuum", emoji: "🧹", placed: false },
    { id: "c2", name: "Dishes", emoji: "🍽", placed: true },
  ],
};
const INV_LAYER: PickerLayer = {
  id: "inventory", label: "Inventory", emoji: "📦",
  items: [
    { id: "i1", name: "TV", emoji: "📺", placed: true },
    { id: "i2", name: "Lamp", emoji: "💡", placed: false },
  ],
};

let target: HTMLElement;

beforeEach(() => {
  target = document.createElement("div");
  document.body.appendChild(target);
});
afterEach(() => {
  target.remove();
});

describe("ItemPickerPanel", () => {
  it("renders a dismiss button when ondismiss is provided, and calls it on click", async () => {
    const ondismiss = vi.fn();
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn(), ondismiss },
    });
    flushSync();
    const btn = target.querySelector('.panel-header [title="Close"]') as HTMLElement;
    expect(btn).not.toBeNull();
    btn.click();
    expect(ondismiss).toHaveBeenCalled();
    unmount(app);
  });

  it("renders no dismiss button when ondismiss is omitted", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    expect(target.querySelector('.panel-header [title="Close"]')).toBeNull();
    unmount(app);
  });

  it("renders a section per layer", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const headers = target.querySelectorAll(".section-header");
    expect(headers.length).toBe(2);
    expect(headers[0].textContent).toContain("Chores");
    expect(headers[1].textContent).toContain("Inventory");
    unmount(app);
  });

  it("single layer is expanded by default", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(1);
    unmount(app);
  });

  it("multiple layers are collapsed by default", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(0);
    unmount(app);
  });

  it("clicking a collapsed section header expands it", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const header = target.querySelector<HTMLButtonElement>(".section-header")!;
    header.click();
    flushSync();
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(1);
    unmount(app);
  });

  it("clicking an expanded section header collapses it", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const header = target.querySelector<HTMLButtonElement>(".section-header")!;
    header.click();
    flushSync();
    expect(target.querySelectorAll(".section-body").length).toBe(0);
    unmount(app);
  });

  it("items split into Unplaced and Placed groups", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const titles = Array.from(target.querySelectorAll(".group-title")).map(el => el.textContent?.trim());
    expect(titles).toContain("Unplaced");
    expect(titles).toContain("Placed");
    unmount(app);
  });

  it("placed items have the .placed class", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const rows = target.querySelectorAll(".item-row");
    const placedRows = Array.from(rows).filter(r => r.classList.contains("placed"));
    expect(placedRows.length).toBe(1);
    unmount(app);
  });

  it("search filters items by name", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown: vi.fn() },
    });
    flushSync();
    const input = target.querySelector<HTMLInputElement>(".search")!;
    input.value = "vacuum";
    input.dispatchEvent(new Event("input"));
    flushSync();
    const names = Array.from(target.querySelectorAll(".item-name")).map(el => el.textContent);
    expect(names).toContain("Vacuum");
    expect(names).not.toContain("Dishes");
    unmount(app);
  });

  it("onitempointerdown called with layerId and item on pointerdown", async () => {
    const onitempointerdown = vi.fn();
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown },
    });
    flushSync();
    const row = target.querySelector<HTMLElement>(".item-row")!;
    row.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
    expect(onitempointerdown).toHaveBeenCalledWith("chores", expect.objectContaining({ id: expect.any(String) }), expect.anything());
    unmount(app);
  });

  it("dragging item gets .dragging class", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: "c1", onitempointerdown: vi.fn() },
    });
    flushSync();
    const rows = target.querySelectorAll(".item-row");
    const draggingRow = Array.from(rows).find(r => r.classList.contains("dragging"));
    expect(draggingRow).toBeTruthy();
    expect(draggingRow?.querySelector(".item-emoji")?.textContent).toBe("🧹");
    unmount(app);
  });

  it("sets touch-action: pan-y on item rows so the list still scrolls on touch", () => {
    // jsdom in this test environment doesn't inject Svelte component <style>
    // blocks into the DOM (verified empirically: document.head has zero
    // <style> tags after mount), so getComputedStyle can never see this rule
    // here -- check the compiled source's CSS block directly instead.
    //
    // touch-action: none here would block native scrolling entirely --
    // since rows fill nearly the whole list, that made the panel
    // unscrollable on touch. pan-y keeps vertical scroll native while
    // leaving horizontal/diagonal pointer movement free for drag-to-place.
    const source = readFileSync("src/lib/components/ItemPickerPanel.svelte", "utf-8");
    const rule = source.slice(source.indexOf(".item-row {"), source.indexOf(".item-row {") + 300);
    expect(rule).toContain("touch-action: pan-y;");
  });
});
