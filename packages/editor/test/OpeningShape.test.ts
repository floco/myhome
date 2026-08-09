import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import OpeningShape from "../src/lib/components/OpeningShape.svelte";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";
import type { Wall, Opening } from "@myhome/geometry";

const wall: Wall = { id: "w1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 };

function makeWindow(overrides: Partial<Opening> = {}): Opening {
  return { id: "o1", wallId: "w1", type: "window", offset: 1, width: 1, ...overrides };
}

function makeDoor(overrides: Partial<Opening> = {}): Opening {
  return { id: "o2", wallId: "w1", type: "door", offset: 1, width: 0.9, ...overrides };
}

let target: HTMLElement;
let app: ReturnType<typeof mount> | undefined;

function setup(props: Record<string, unknown>) {
  target = document.createElement("div");
  document.body.appendChild(target);
  app = mount(OpeningShape, {
    target,
    props: { wall, viewport: { ...DEFAULT_VIEWPORT }, ...props },
  });
  flushSync();
}

afterEach(() => {
  if (app) { unmount(app); app = undefined; }
  target?.remove();
});

describe("OpeningShape — HA sensor color", () => {
  it("renders the default color when the ha layer is off, even if linked", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: false,
      haState: { state: "on", attributes: {} },
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-window)");
  });

  it("renders open color when the sensor state is 'on'", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: true,
      haState: { state: "on", attributes: {} },
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-open)");
  });

  it("renders default color when the sensor state is 'off'", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: true,
      haState: { state: "off", attributes: {} },
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-window)");
  });

  it("renders unavailable color when state is missing", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: true,
      haState: null,
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-unavailable)");
  });

  it("renders the default color for an unlinked opening even with the layer on", () => {
    setup({ opening: makeWindow(), haLayerActive: true });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-window)");
  });
});

describe("OpeningShape — shutter overlay", () => {
  it("renders no overlay when hasShutter is false", () => {
    setup({
      opening: makeWindow({ hasShutter: false }),
      haLayerActive: true,
    });
    expect(target.querySelector(".shutter-overlay")).toBeNull();
  });

  it("renders an overlay proportional to the closed fraction via current_position", () => {
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      haLayerActive: true,
      shutterState: { state: "open", attributes: { current_position: 50 } },
    });
    const overlay = target.querySelector(".shutter-overlay");
    expect(overlay).not.toBeNull();
  });

  it("renders a full overlay when current_position is absent and state is 'closed'", () => {
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      haLayerActive: true,
      shutterState: { state: "closed", attributes: {} },
    });
    expect(target.querySelector(".shutter-overlay")).not.toBeNull();
  });

  it("renders no overlay when current_position is 100 (fully open)", () => {
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      haLayerActive: true,
      shutterState: { state: "open", attributes: { current_position: 100 } },
    });
    expect(target.querySelector(".shutter-overlay")).toBeNull();
  });

  it("has no click handler of its own, so it can't swallow clicks meant for the shapes underneath", () => {
    let selectedId: string | null = null;
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      haLayerActive: true,
      shutterState: { state: "closed", attributes: {} },
      tool: "select",
      onselect: (id: string) => { selectedId = id; },
    });
    const overlay = target.querySelector(".shutter-overlay") as SVGPolygonElement;
    expect(overlay).not.toBeNull();
    overlay.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(selectedId).toBeNull();

    const gap = target.querySelector("polygon:not(.shutter-overlay)") as SVGPolygonElement;
    gap.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(selectedId).toBe("o1");
  });
});

describe("OpeningShape — window glazing symbol", () => {
  it("renders two window-sym lines offset toward the interior by default", () => {
    setup({ opening: makeWindow({ offset: 1, width: 1 }) });
    const lines = target.querySelectorAll("line.window-sym");
    expect(lines).toHaveLength(2);
    // wall runs along +x, thickness 0.1 -> "in" perpendicular is world +y (screen y increases).
    expect(Number((lines[0] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(303, 5);
    expect(Number((lines[1] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(301, 5);
  });

  it("offsets both lines toward the exterior when windowSide is out", () => {
    setup({ opening: makeWindow({ offset: 1, width: 1, windowSide: "out" }) });
    const lines = target.querySelectorAll("line.window-sym");
    expect(Number((lines[0] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(297, 5);
    expect(Number((lines[1] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(299, 5);
  });
});

describe("OpeningShape — door kind rendering", () => {
  it("renders one leaf/arc pair for hinged (default) doorKind", () => {
    setup({ opening: makeDoor({ swing: "left-in" }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(1);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(1);
  });

  it("renders two leaf/arc pairs for swinging (battante) doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "swinging", swing: "left-in" }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(2);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(2);
  });

  it("renders a sliding bar with no arc for sliding doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "sliding" }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(0);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(0);
    expect(target.querySelectorAll("line.door-sliding")).toHaveLength(1);
  });

  it("renders hatch ticks with no arc for garage doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "garage" }) });
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(0);
    expect(target.querySelectorAll("line.door-garage")).toHaveLength(5);
  });

  it("colors sliding and garage doors with the same strokeColor logic as hinged", () => {
    setup({ opening: makeDoor({ doorKind: "sliding" }), selected: true });
    const line = target.querySelector("line.door-sliding") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-wall-selected)");
  });

  it("renders two independent leaf/arc pairs for double doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6 }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(2);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(2);
  });

  it("hinges the double door's two leaves at the opening's own start and end points", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6 }) });
    const leaves = target.querySelectorAll("line.door-leaf");
    // wall (0,0)->(4,0), DEFAULT_VIEWPORT panX:400 panY:300 zoom:100 -> world x=1 -> screen x=500, world x=2.6 -> screen x=660.
    const x1s = [Number(leaves[0].getAttribute("x1")), Number(leaves[1].getAttribute("x1"))].sort((a, b) => a - b);
    expect(x1s[0]).toBeCloseTo(500, 5);
    expect(x1s[1]).toBeCloseTo(660, 5);
  });

  it("swings both double-door leaves outward when swing is out", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6, swing: "out" }) });
    const leaves = target.querySelectorAll("line.door-leaf");
    // "out" perpendicular for a wall along +x is world -y (screen y decreases from the 300 baseline).
    for (const leaf of leaves) {
      expect(Number((leaf as SVGLineElement).getAttribute("y2"))).toBeLessThan(300);
    }
  });

  it("defaults double door swing to in when unset", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6 }) });
    const leaves = target.querySelectorAll("line.door-leaf");
    for (const leaf of leaves) {
      expect(Number((leaf as SVGLineElement).getAttribute("y2"))).toBeGreaterThan(300);
    }
  });
});
