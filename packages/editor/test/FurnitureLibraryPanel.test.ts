import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import FurnitureLibraryPanel from "../src/lib/components/FurnitureLibraryPanel.svelte";
import { FURNITURE_TEMPLATES } from "../src/lib/furnitureLibrary";

describe("FurnitureLibraryPanel", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) { unmount(app); app = undefined; }
    target?.remove();
  });

  function setup(props: Record<string, unknown> = {}) {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = mount(FurnitureLibraryPanel, { target, props });
    flushSync();
    return target;
  }

  it("renders the search input", () => {
    setup();
    const input = target.querySelector("input[type='search'], input[placeholder]");
    expect(input).not.toBeNull();
  });

  it("renders all categories as section headings", () => {
    setup();
    const headings = Array.from(target.querySelectorAll(".category-label")).map(
      (el) => el.textContent?.trim(),
    );
    expect(headings).toContain("Living Room");
    expect(headings).toContain("Garden");
  });

  it("renders all templates with draggable items", () => {
    setup();
    const items = target.querySelectorAll("[draggable='true']");
    expect(items.length).toBe(FURNITURE_TEMPLATES.length);
  });

  it("filters items when search text is entered", async () => {
    const { tick } = await import("svelte");
    setup();
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "sofa";
    input.dispatchEvent(new Event("input"));
    await tick();
    flushSync();
    const items = target.querySelectorAll("[draggable='true']");
    expect(items.length).toBe(1);
    expect(items[0].getAttribute("data-template-id")).toBe("sofa");
  });

  it("shows all items when search is cleared", async () => {
    const { tick } = await import("svelte");
    setup();
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "sofa";
    input.dispatchEvent(new Event("input"));
    await tick();
    input.value = "";
    input.dispatchEvent(new Event("input"));
    await tick();
    flushSync();
    const items = target.querySelectorAll("[draggable='true']");
    expect(items.length).toBe(FURNITURE_TEMPLATES.length);
  });

  it("renders every thumbnail SVG at the same uniform size regardless of the template's real-world aspect ratio", () => {
    setup();
    const svgs = Array.from(target.querySelectorAll(".furniture-item svg"));
    expect(svgs.length).toBe(FURNITURE_TEMPLATES.length);
    const widths = new Set(svgs.map((el) => el.getAttribute("width")));
    const heights = new Set(svgs.map((el) => el.getAttribute("height")));
    expect(widths.size).toBe(1);
    expect(heights.size).toBe(1);
    expect([...widths][0]).toBe([...heights][0]);
  });
});
