import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import FurnitureShape from "../src/lib/components/FurnitureShape.svelte";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";
import type { FurnitureObject } from "@myhome/geometry";
import { getTemplate } from "../src/lib/furnitureLibrary";

const VP = { ...DEFAULT_VIEWPORT };

function makeSofa(): FurnitureObject {
  return { id: "f1", templateId: "sofa", x: 2, y: 1.5, width: 2.2, height: 0.9, rotation: 0 };
}

describe("FurnitureShape", () => {
  let target: HTMLElement;
  let svg: SVGSVGElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) { unmount(app); app = undefined; }
    target?.remove();
  });

  function setup(props: Record<string, unknown>) {
    target = document.createElement("div");
    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
    target.appendChild(svg);
    document.body.appendChild(target);
    app = mount(FurnitureShape, { target: svg, props });
    flushSync();
    return svg;
  }

  it("renders a <g> with the correct transform", () => {
    const object = makeSofa();
    const template = getTemplate("sofa")!;
    setup({ object, template, viewport: VP, selected: false, tool: "select" });
    const g = svg.querySelector("g.furniture-object");
    expect(g).not.toBeNull();
    expect(g!.getAttribute("transform")).toContain("rotate(0)");
  });

  it("adds .selected class when selected=true", () => {
    const object = makeSofa();
    const template = getTemplate("sofa")!;
    setup({ object, template, viewport: VP, selected: true, tool: "select" });
    const g = svg.querySelector("g.furniture-object");
    expect(g!.classList.contains("selected")).toBe(true);
  });

  it("does not add .selected class when selected=false", () => {
    const object = makeSofa();
    const template = getTemplate("sofa")!;
    setup({ object, template, viewport: VP, selected: false, tool: "select" });
    const g = svg.querySelector("g.furniture-object");
    expect(g!.classList.contains("selected")).toBe(false);
  });

  it("calls onselect when the body is clicked", () => {
    const onselect = vi.fn();
    const object = makeSofa();
    const template = getTemplate("sofa")!;
    setup({ object, template, viewport: VP, selected: false, tool: "select", onselect });
    const g = svg.querySelector("g.furniture-object");
    g!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onselect).toHaveBeenCalledWith("f1");
  });

  it("applies rotation in the transform", () => {
    const object = { ...makeSofa(), rotation: 45 };
    const template = getTemplate("sofa")!;
    setup({ object, template, viewport: VP, selected: false, tool: "select" });
    const g = svg.querySelector("g.furniture-object");
    expect(g!.getAttribute("transform")).toContain("rotate(45)");
  });
});
