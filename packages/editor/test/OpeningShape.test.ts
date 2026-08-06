import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import OpeningShape from "../src/lib/components/OpeningShape.svelte";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";
import type { Wall, Opening } from "@myhome/geometry";

const wall: Wall = { id: "w1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 };

function makeWindow(overrides: Partial<Opening> = {}): Opening {
  return { id: "o1", wallId: "w1", type: "window", offset: 1, width: 1, ...overrides };
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
});
