import type { Point } from "@myhome/geometry";

export interface ViewportState {
  panX: number;
  panY: number;
  zoom: number;
}

export const DEFAULT_VIEWPORT: ViewportState = { panX: 400, panY: 300, zoom: 100 };

export function createViewportStore() {
  const viewport = $state<ViewportState>({ ...DEFAULT_VIEWPORT });

  function worldToScreen(p: Point): Point {
    return { x: p.x * viewport.zoom + viewport.panX, y: p.y * viewport.zoom + viewport.panY };
  }

  function screenToWorld(p: Point): Point {
    return { x: (p.x - viewport.panX) / viewport.zoom, y: (p.y - viewport.panY) / viewport.zoom };
  }

  function zoomAt(screenPoint: Point, factor: number): void {
    const worldPoint = screenToWorld(screenPoint);
    viewport.zoom *= factor;
    viewport.panX = screenPoint.x - worldPoint.x * viewport.zoom;
    viewport.panY = screenPoint.y - worldPoint.y * viewport.zoom;
  }

  function pan(dx: number, dy: number): void {
    viewport.panX += dx;
    viewport.panY += dy;
  }

  function reset(): void {
    viewport.panX = DEFAULT_VIEWPORT.panX;
    viewport.panY = DEFAULT_VIEWPORT.panY;
    viewport.zoom = DEFAULT_VIEWPORT.zoom;
  }

  return {
    get viewport() {
      return viewport;
    },
    worldToScreen,
    screenToWorld,
    zoomAt,
    pan,
    reset,
  };
}
