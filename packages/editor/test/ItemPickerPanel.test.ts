import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
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
  it("renders a section per layer", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
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
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    flushSync();
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(1);
    unmount(app);
  });

  it("multiple layers are collapsed by default", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    flushSync();
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(0);
    unmount(app);
  });

  it("clicking a collapsed section header expands it", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
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
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
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
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
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
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
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
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
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

  it("ondragstart called with layerId and itemId on drag", async () => {
    const ondragstart = vi.fn();
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart, ondragend: vi.fn() },
    });
    flushSync();
    const row = target.querySelector<HTMLElement>(".item-row")!;
    const dt = { setDragImage: vi.fn(), setData: vi.fn() };
    const evt = new MouseEvent("dragstart", { bubbles: true }) as unknown as DragEvent;
    Object.defineProperty(evt, "dataTransfer", { value: dt });
    row.dispatchEvent(evt);
    await Promise.resolve();
    expect(ondragstart).toHaveBeenCalledWith("chores", expect.any(String), expect.anything());
    unmount(app);
  });

  it("dragging item gets .dragging class", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: "c1", ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    flushSync();
    const rows = target.querySelectorAll(".item-row");
    const draggingRow = Array.from(rows).find(r => r.classList.contains("dragging"));
    expect(draggingRow).toBeTruthy();
    expect(draggingRow?.querySelector(".item-emoji")?.textContent).toBe("🧹");
    unmount(app);
  });
});
