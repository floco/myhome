import type { Floor } from "@myhome/geometry";
import { allEndpoints } from "./drawingTool";
import type { ViewportState } from "./viewportStore.svelte";

export function fitViewportToFloor(
  floor: Floor,
  width: number,
  height: number,
  padding = 40
): ViewportState {
  const points = allEndpoints(floor.walls);
  if (points.length === 0) {
    return { panX: width / 2, panY: height / 2, zoom: 100 };
  }

  const minX = Math.min(...points.map((p) => p.x));
  const maxX = Math.max(...points.map((p) => p.x));
  const minY = Math.min(...points.map((p) => p.y));
  const maxY = Math.max(...points.map((p) => p.y));

  const spanX = Math.max(maxX - minX, 0.1);
  const spanY = Math.max(maxY - minY, 0.1);
  const availW = Math.max(width - padding * 2, 1);
  const availH = Math.max(height - padding * 2, 1);
  const zoom = Math.min(availW / spanX, availH / spanY);

  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  return {
    panX: width / 2 - cx * zoom,
    panY: height / 2 - cy * zoom,
    zoom,
  };
}
