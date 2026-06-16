import type { Point } from "@myhome/geometry";

export interface ViewportState {
  panX: number;
  panY: number;
  zoom: number;
}

export const DEFAULT_VIEWPORT: ViewportState = { panX: 400, panY: 300, zoom: 100 };

const MIN_ZOOM = 20;   // 2 cm/pixel — ~2,400 grid lines max
const MAX_ZOOM = 2000; // 0.05 mm/pixel

export function createViewportStore() {
  const viewport = $state<ViewportState>({ ...DEFAULT_VIEWPORT });

  function worldToScreen(p: Point): Point {
    return { x: p.x * viewport.zoom + viewport.panX, y: p.y * viewport.zoom + viewport.panY };
  }

  function screenToWorld(p: Point): Point {
    return { x: (p.x - viewport.panX) / viewport.zoom, y: (p.y - viewport.panY) / viewport.zoom };
  }

  function zoomAt(screen: Point, factor: number): void {
    const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewport.zoom * factor));
    const actualFactor = newZoom / viewport.zoom;
    viewport.panX = screen.x - actualFactor * (screen.x - viewport.panX);
    viewport.panY = screen.y - actualFactor * (screen.y - viewport.panY);
    viewport.zoom = newZoom;
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
