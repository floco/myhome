// packages/editor/src/lib/treemapLayout.ts

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

function worstRatio(row: number[], shortSide: number): number {
  const sum = row.reduce((a, b) => a + b, 0);
  const rowMax = Math.max(...row);
  const rowMin = Math.min(...row);
  return Math.max(
    (shortSide * shortSide * rowMax) / (sum * sum),
    (sum * sum) / (shortSide * shortSide * rowMin),
  );
}

function layoutRow(row: number[], rect: Rect, horizontal: boolean): Rect[] {
  const sum = row.reduce((a, b) => a + b, 0);
  const rects: Rect[] = [];
  if (horizontal) {
    const rowHeight = sum / rect.w;
    let x = rect.x;
    for (const v of row) {
      const w = v / rowHeight;
      rects.push({ x, y: rect.y, w, h: rowHeight });
      x += w;
    }
  } else {
    const rowWidth = sum / rect.h;
    let y = rect.y;
    for (const v of row) {
      const h = v / rowWidth;
      rects.push({ x: rect.x, y, w: rowWidth, h });
      y += h;
    }
  }
  return rects;
}

/** Squarified treemap (Bruls, Huizing, van Wijk) — packs cells to stay near-square. */
function squarify(values: number[], rect: Rect): Rect[] {
  if (values.length === 0 || rect.w <= 0 || rect.h <= 0) return values.map(() => ({ x: rect.x, y: rect.y, w: 0, h: 0 }));

  const horizontal = rect.w >= rect.h;
  const shortSide = horizontal ? rect.h : rect.w;

  let row: number[] = [];
  let i = 0;
  while (i < values.length) {
    const candidate = [...row, values[i]];
    if (row.length === 0 || worstRatio(candidate, shortSide) <= worstRatio(row, shortSide)) {
      row = candidate;
      i++;
    } else {
      break;
    }
  }

  const rowRects = layoutRow(row, rect, horizontal);
  const rowSum = row.reduce((a, b) => a + b, 0);

  const remainingRect: Rect = horizontal
    ? { x: rect.x, y: rect.y + rowSum / rect.w, w: rect.w, h: rect.h - rowSum / rect.w }
    : { x: rect.x + rowSum / rect.h, y: rect.y, w: rect.w - rowSum / rect.h, h: rect.h };

  return [...rowRects, ...squarify(values.slice(row.length), remainingRect)];
}

/**
 * Lays out `values` as a squarified treemap filling `width x height`,
 * returning one Rect per value in the same order as the input.
 */
export function computeTreemap(values: number[], width: number, height: number): Rect[] {
  if (values.length === 0) return [];
  const total = values.reduce((a, b) => a + b, 0);
  if (total <= 0) return values.map(() => ({ x: 0, y: 0, w: 0, h: 0 }));
  const area = width * height;
  const scaled = values.map((v) => (v / total) * area);
  return squarify(scaled, { x: 0, y: 0, w: width, h: height });
}

/** Decides how much content a treemap cell of size w x h can hold. */
export function cellContentTier(w: number, h: number): "label" | "icon" | "none" {
  if (w >= 64 && h >= 36) return "label";
  if (w >= 22 && h >= 22) return "icon";
  return "none";
}
