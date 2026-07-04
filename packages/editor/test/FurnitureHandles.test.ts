import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import FurnitureHandles from "../src/lib/components/FurnitureHandles.svelte";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";
import type { FurnitureObject } from "@myhome/geometry";

const VP = { ...DEFAULT_VIEWPORT };

function makeSofa(): FurnitureObject {
  return { id: "f1", templateId: "sofa", x: 2, y: 1.5, width: 2.2, height: 0.9, rotation: 0 };
}

describe("FurnitureHandles", () => {
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
    app = mount(FurnitureHandles, { target: svg, props });
    flushSync();
    return svg;
  }

  it("renders 4 corner handles", () => {
    const object = makeSofa();
    setup({ object, viewport: VP });
    const handles = svg.querySelectorAll("rect.corner-handle");
    expect(handles).toHaveLength(4);
  });

  it("renders 1 rotate handle", () => {
    const object = makeSofa();
    setup({ object, viewport: VP });
    const handle = svg.querySelectorAll("circle.rotate-handle");
    expect(handle).toHaveLength(1);
  });

  it("calls onresizestart when a corner handle is mousedown'd", () => {
    const onresizestart = vi.fn();
    const object = makeSofa();
    setup({ object, viewport: VP, onresizestart });
    const handle = svg.querySelector("rect.corner-handle")!;
    handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(onresizestart).toHaveBeenCalled();
    const [id, corner] = onresizestart.mock.calls[0];
    expect(id).toBe("f1");
    expect(typeof corner).toBe("string");
  });

  it("calls onrotatestart when the rotate handle is mousedown'd", () => {
    const onrotatestart = vi.fn();
    const object = makeSofa();
    setup({ object, viewport: VP, onrotatestart });
    const handle = svg.querySelector("circle.rotate-handle")!;
    handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(onrotatestart).toHaveBeenCalledWith("f1", expect.any(MouseEvent));
  });
});
