import { describe, it, expect } from "vitest";
import { createFloatingDrag } from "../src/lib/floatingDrag.svelte";

function setUpDom(): { container: HTMLElement; panel: HTMLElement } {
  const container = document.createElement("div");
  container.style.cssText = "position:relative;width:800px;height:600px;";
  document.body.appendChild(container);
  const panel = document.createElement("div");
  panel.className = "test-panel";
  panel.style.cssText = "width:100px;height:50px;";
  container.appendChild(panel);
  container.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 600, right: 800, bottom: 600, x: 0, y: 0, toJSON() {} });
  // Positioned away from the container's bottom-right edge so a normal-sized
  // drag delta doesn't accidentally land on the clamp boundary.
  panel.getBoundingClientRect = () => ({ left: 300, top: 200, width: 100, height: 50, right: 400, bottom: 250, x: 300, y: 200, toJSON() {} });
  return { container, panel };
}

describe("createFloatingDrag", () => {
  it("pos starts null", () => {
    const drag = createFloatingDrag(".test-panel");
    expect(drag.pos).toBeNull();
  });

  it("dragging moves pos by the mouse delta, clamped to the container bounds", () => {
    const { container, panel } = setUpDom();
    const drag = createFloatingDrag(".test-panel");
    const mousedown = new MouseEvent("mousedown", { bubbles: true, clientX: 350, clientY: 225 });
    Object.defineProperty(mousedown, "currentTarget", { value: panel });
    drag.startDrag(mousedown);
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 370, clientY: 245 }));
    // initX=300, initY=200, delta=(20,20) -> (320, 220), well within the 800x600 container.
    expect(drag.pos).toEqual({ x: 320, y: 220 });
    window.dispatchEvent(new MouseEvent("mouseup"));
    panel.remove();
    container.remove();
  });

  it("clamps to the container's bottom-right when dragged past it", () => {
    const { container, panel } = setUpDom();
    const drag = createFloatingDrag(".test-panel");
    const mousedown = new MouseEvent("mousedown", { bubbles: true, clientX: 350, clientY: 225 });
    Object.defineProperty(mousedown, "currentTarget", { value: panel });
    drag.startDrag(mousedown);
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 5000, clientY: 5000 }));
    // container width(800) - panel width(100) = 700 max x; height(600) - 50 = 550 max y.
    expect(drag.pos).toEqual({ x: 700, y: 550 });
    window.dispatchEvent(new MouseEvent("mouseup"));
    panel.remove();
    container.remove();
  });
});
