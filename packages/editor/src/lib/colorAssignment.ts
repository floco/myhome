// packages/editor/src/lib/colorAssignment.ts

function hashString(str: string): number {
  let h = 0;
  for (const ch of str) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h;
}

function generatedColor(indexBeyondPalette: number, totalBeyondPalette: number): string {
  const hue = (indexBeyondPalette * 360) / totalBeyondPalette;
  return `hsl(${hue.toFixed(2)}, 60%, 55%)`;
}

const BASE_PALETTE_SIZE = 8;

/**
 * Assigns each category a color guaranteed distinct from every other category
 * currently in the set. Uses open addressing (hash + linear probe) into a
 * slot array sized to the category count, so every category is guaranteed a
 * free slot — no collisions possible. The first 8 slots map to the validated
 * `--chart-series-N` tokens; slots beyond that get an evenly-spaced generated
 * hue (there are exactly as many extra hues as extra slots, so those stay
 * distinct too).
 */
export function assignCategoryColors(categories: string[]): Map<string, string> {
  const sorted = [...new Set(categories)].sort();
  const n = sorted.length;
  if (n === 0) return new Map();

  const usedSlots = new Set<number>();
  const result = new Map<string, string>();
  const extraCount = Math.max(0, n - BASE_PALETTE_SIZE);

  for (const category of sorted) {
    let slot = hashString(category) % n;
    while (usedSlots.has(slot)) {
      slot = (slot + 1) % n;
    }
    usedSlots.add(slot);

    const color =
      slot < BASE_PALETTE_SIZE
        ? `var(--chart-series-${slot + 1})`
        : generatedColor(slot - BASE_PALETTE_SIZE, extraCount);
    result.set(category, color);
  }

  return result;
}
