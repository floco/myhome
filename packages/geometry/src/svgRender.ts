import type { Floor, Wall, Opening, Room, Point, DoorSwing } from "./types";

export interface SvgRenderOptions {
  /** Padding (in meters) added around the computed bounding box. Default 0.5. */
  padding?: number;
}

interface Bounds {
  minX: number;
  minY: number;
  width: number;
  height: number;
}

/**
 * Renders a floor (walls, dividers, openings, rooms) as an SVG document.
 * Coordinates are emitted 1:1 in meters; the viewBox is fit to the floor's
 * wall bounding box plus padding, so consumers can scale to pixels via
 * width/height or CSS.
 */
export function renderFloorSvg(floor: Floor, options: SvgRenderOptions = {}): string {
  const padding = options.padding ?? 0.5;
  const bounds = computeBounds(floor.walls, padding);

  const roomsSvg = floor.rooms
    .filter((r): r is Room & { polygon: Point[] } => r.polygon !== null)
    .map(renderRoom)
    .join("\n");

  const wallsSvg = floor.walls
    .filter((w) => w.type === "wall")
    .map((w) => renderWall(w, floor.openings.filter((o) => o.wallId === w.id)))
    .join("\n");

  const dividersSvg = floor.walls
    .filter((w) => w.type === "divider")
    .map(renderDivider)
    .join("\n");

  const openingsSvg = floor.walls
    .flatMap((w) =>
      w.type === "wall"
        ? floor.openings.filter((o) => o.wallId === w.id).map((o) => renderOpening(w, o))
        : []
    )
    .join("\n");

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${fmt(bounds.minX)} ${fmt(bounds.minY)} ${fmt(bounds.width)} ${fmt(bounds.height)}">`,
    `<g class="rooms">`,
    roomsSvg,
    `</g>`,
    `<g class="walls">`,
    wallsSvg,
    `</g>`,
    `<g class="dividers">`,
    dividersSvg,
    `</g>`,
    `<g class="openings">`,
    openingsSvg,
    `</g>`,
    `</svg>`,
  ].join("\n");
}

function computeBounds(walls: Wall[], padding: number): Bounds {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const w of walls) {
    for (const p of [w.start, w.end]) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
  }
  if (!isFinite(minX)) {
    minX = 0;
    minY = 0;
    maxX = 0;
    maxY = 0;
  }
  return {
    minX: minX - padding,
    minY: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  };
}

function renderRoom(room: Room & { polygon: Point[] }): string {
  const d = polygonToPath(room.polygon);
  const haArea = room.haAreaId ?? "";
  return `<path id="room-${escapeAttr(room.id)}" data-ha-area="${escapeAttr(haArea)}" class="room" d="${d}" />`;
}

function renderDivider(wall: Wall): string {
  return `<path class="divider" d="${polylineToPath([wall.start, wall.end])}" stroke-dasharray="0.1 0.1" />`;
}

function renderWall(wall: Wall, openings: Opening[]): string {
  const thickness = wall.thickness ?? 0.1;
  const { dirX, dirY, length } = wallDirection(wall);
  if (length < 1e-9) return "";

  const perpX = -dirY * (thickness / 2);
  const perpY = dirX * (thickness / 2);

  const gaps = openings
    .map((o) => {
      const from = clamp(o.offset, 0, length);
      const to = clamp(o.offset + o.width, from, length);
      return { from, to };
    })
    .sort((a, b) => a.from - b.from);

  const segments: { from: number; to: number }[] = [];
  let cursor = 0;
  for (const gap of gaps) {
    if (gap.from > cursor) segments.push({ from: cursor, to: gap.from });
    cursor = Math.max(cursor, gap.to);
  }
  if (cursor < length) segments.push({ from: cursor, to: length });

  return segments
    .map((seg) => {
      const p1 = pointAlong(wall.start, dirX, dirY, seg.from);
      const p2 = pointAlong(wall.start, dirX, dirY, seg.to);
      const corners: Point[] = [
        { x: p1.x + perpX, y: p1.y + perpY },
        { x: p2.x + perpX, y: p2.y + perpY },
        { x: p2.x - perpX, y: p2.y - perpY },
        { x: p1.x - perpX, y: p1.y - perpY },
      ];
      return `<path class="wall" d="${polygonToPath(corners)}" />`;
    })
    .join("\n");
}

function renderOpening(wall: Wall, opening: Opening): string {
  const { dirX, dirY, length } = wallDirection(wall);
  const from = clamp(opening.offset, 0, length);
  const to = clamp(opening.offset + opening.width, from, length);
  const renderWidth = to - from;

  const p1 = pointAlong(wall.start, dirX, dirY, from);
  const p2 = pointAlong(wall.start, dirX, dirY, to);

  if (opening.type === "window") {
    return `<line class="window" x1="${fmt(p1.x)}" y1="${fmt(p1.y)}" x2="${fmt(p2.x)}" y2="${fmt(p2.y)}" />`;
  }

  return renderDoor(p1, p2, dirX, dirY, opening.swing ?? "left-in", renderWidth);
}

function renderDoor(
  p1: Point,
  p2: Point,
  dirX: number,
  dirY: number,
  swing: DoorSwing,
  width: number
): string {
  if (width < 1e-9) return "";

  const perpLeft: Point = { x: -dirY, y: dirX };
  const perpRight: Point = { x: dirY, y: -dirX };

  const isLeftHinge = swing === "left-in" || swing === "left-out";
  const isInSwing = swing === "left-in" || swing === "right-in";

  const hinge = isLeftHinge ? p1 : p2;
  const other = isLeftHinge ? p2 : p1;
  const perp = isInSwing ? perpLeft : perpRight;

  const openEnd: Point = {
    x: hinge.x + perp.x * width,
    y: hinge.y + perp.y * width,
  };

  const leaf = `<line class="door-leaf" x1="${fmt(hinge.x)}" y1="${fmt(hinge.y)}" x2="${fmt(openEnd.x)}" y2="${fmt(openEnd.y)}" />`;

  const sweepFlag = chooseSweepFlag(other, openEnd, width, hinge);
  const arc = `<path class="door-swing" d="M ${fmt(other.x)} ${fmt(other.y)} A ${fmt(width)} ${fmt(width)} 0 0 ${sweepFlag} ${fmt(openEnd.x)} ${fmt(openEnd.y)}" />`;

  return `${leaf}\n${arc}`;
}

/**
 * Picks the SVG arc sweep-flag (with large-arc-flag fixed at 0) that makes
 * the resulting arc's center coincide with `desiredCenter`, using the
 * standard endpoint-to-center arc conversion (rx === ry === radius, no
 * rotation). https://www.w3.org/TR/SVG/implnote.html#ArcConversionEndpointToCenter
 */
export function chooseSweepFlag(
  start: Point,
  end: Point,
  radius: number,
  desiredCenter: Point
): 0 | 1 {
  const x1p = (start.x - end.x) / 2;
  const y1p = (start.y - end.y) / 2;
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;
  const sumSq = x1p * x1p + y1p * y1p;
  const term = Math.max((radius * radius - sumSq) / sumSq, 0);
  const factor = Math.sqrt(term);

  // sweep-flag 0 -> coefficient = -factor; sweep-flag 1 -> coefficient = +factor
  const center0: Point = { x: midX - factor * y1p, y: midY + factor * x1p };
  const center1: Point = { x: midX + factor * y1p, y: midY - factor * x1p };

  const d0 = Math.hypot(center0.x - desiredCenter.x, center0.y - desiredCenter.y);
  const d1 = Math.hypot(center1.x - desiredCenter.x, center1.y - desiredCenter.y);
  return d0 <= d1 ? 0 : 1;
}

function wallDirection(wall: Wall): { dirX: number; dirY: number; length: number } {
  const dx = wall.end.x - wall.start.x;
  const dy = wall.end.y - wall.start.y;
  const length = Math.hypot(dx, dy);
  if (length < 1e-9) return { dirX: 0, dirY: 0, length };
  return { dirX: dx / length, dirY: dy / length, length };
}

function pointAlong(start: Point, dirX: number, dirY: number, distance: number): Point {
  return { x: start.x + dirX * distance, y: start.y + dirY * distance };
}

function clamp(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), Math.max(min, max));
}

function polygonToPath(points: Point[]): string {
  const [first, ...rest] = points;
  const parts = [`M ${fmt(first.x)} ${fmt(first.y)}`];
  for (const p of rest) parts.push(`L ${fmt(p.x)} ${fmt(p.y)}`);
  parts.push("Z");
  return parts.join(" ");
}

function polylineToPath(points: Point[]): string {
  const [first, ...rest] = points;
  const parts = [`M ${fmt(first.x)} ${fmt(first.y)}`];
  for (const p of rest) parts.push(`L ${fmt(p.x)} ${fmt(p.y)}`);
  return parts.join(" ");
}

function fmt(n: number): string {
  return String(Math.round(n * 1000) / 1000);
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}
