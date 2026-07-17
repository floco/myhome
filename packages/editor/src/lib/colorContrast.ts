// packages/editor/src/lib/colorContrast.ts

function parseHex(hex: string): [number, number, number] | null {
  const m = /^#([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  const int = parseInt(m[1], 16);
  return [(int >> 16) & 255, (int >> 8) & 255, int & 255];
}

/** Perceived brightness on a 0-255 scale (ITU-R BT.601 weights). */
function brightness(r: number, g: number, b: number): number {
  return (r * 299 + g * 587 + b * 114) / 1000;
}

/**
 * Picks readable ink for text placed directly on an arbitrary fill color
 * (e.g. a donut wedge's inside label). Falls back to dark text when the
 * input isn't a parseable `#rrggbb` hex string (e.g. a CSS variable
 * reference).
 */
export function textColorForFill(hex: string): "#ffffff" | "#111111" {
  const rgb = parseHex(hex);
  if (!rgb) return "#111111";
  const [r, g, b] = rgb;
  return brightness(r, g, b) > 140 ? "#111111" : "#ffffff";
}
