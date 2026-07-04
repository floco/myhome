export type FurnitureCategory =
  | "living-room"
  | "bedroom"
  | "kitchen-dining"
  | "bathroom"
  | "office"
  | "outdoor"
  | "garden";

export const FURNITURE_CATEGORIES: FurnitureCategory[] = [
  "living-room", "bedroom", "kitchen-dining", "bathroom", "office", "outdoor", "garden",
];

export const CATEGORY_LABELS: Record<FurnitureCategory, string> = {
  "living-room": "Living Room",
  "bedroom": "Bedroom",
  "kitchen-dining": "Kitchen & Dining",
  "bathroom": "Bathroom",
  "office": "Office",
  "outdoor": "Outdoor",
  "garden": "Garden",
};

export interface FurnitureTemplate {
  id: string;
  label: string;
  category: FurnitureCategory;
  defaultWidth: number;
  defaultHeight: number;
  svgContent: string;
}

export const FURNITURE_TEMPLATES: FurnitureTemplate[] = [
  // ── Living Room ──────────────────────────────────────────
  {
    id: "sofa",
    label: "Sofa",
    category: "living-room",
    defaultWidth: 2.2,
    defaultHeight: 0.9,
    svgContent: `
      <rect x="8" y="18" width="84" height="68" rx="6"/>
      <rect x="8" y="18" width="84" height="22" rx="4"/>
      <rect x="8" y="40" width="14" height="46" rx="3"/>
      <rect x="78" y="40" width="14" height="46" rx="3"/>
      <line x1="42" y1="40" x2="42" y2="86" fill="none" stroke-width="1.5"/>
      <line x1="58" y1="40" x2="58" y2="86" fill="none" stroke-width="1.5"/>
    `,
  },
  {
    id: "armchair",
    label: "Armchair",
    category: "living-room",
    defaultWidth: 1.0,
    defaultHeight: 0.9,
    svgContent: `
      <rect x="10" y="18" width="80" height="70" rx="6"/>
      <rect x="10" y="18" width="80" height="24" rx="4"/>
      <rect x="10" y="42" width="14" height="46" rx="3"/>
      <rect x="76" y="42" width="14" height="46" rx="3"/>
    `,
  },
  {
    id: "coffee-table",
    label: "Coffee Table",
    category: "living-room",
    defaultWidth: 1.2,
    defaultHeight: 0.6,
    svgContent: `
      <rect x="8" y="8" width="84" height="84" rx="4"/>
      <rect x="16" y="16" width="68" height="68" rx="2" fill="none"/>
    `,
  },
  {
    id: "tv-unit",
    label: "TV Unit",
    category: "living-room",
    defaultWidth: 1.8,
    defaultHeight: 0.45,
    svgContent: `
      <rect x="5" y="20" width="90" height="60" rx="3"/>
      <line x1="5" y1="38" x2="95" y2="38" fill="none"/>
      <rect x="28" y="24" width="44" height="11" rx="1" fill="none"/>
    `,
  },
  {
    id: "bookshelf",
    label: "Bookshelf",
    category: "living-room",
    defaultWidth: 1.2,
    defaultHeight: 0.3,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="2"/>
      <line x1="5" y1="28" x2="95" y2="28" fill="none"/>
      <line x1="5" y1="51" x2="95" y2="51" fill="none"/>
      <line x1="5" y1="74" x2="95" y2="74" fill="none"/>
      <line x1="50" y1="5" x2="50" y2="95" fill="none"/>
    `,
  },
  // ── Bedroom ──────────────────────────────────────────────
  {
    id: "bed-single",
    label: "Single Bed",
    category: "bedroom",
    defaultWidth: 1.0,
    defaultHeight: 2.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="4"/>
      <rect x="12" y="8" width="76" height="28" rx="14"/>
      <line x1="5" y1="38" x2="95" y2="38" fill="none"/>
    `,
  },
  {
    id: "bed-double",
    label: "Double Bed",
    category: "bedroom",
    defaultWidth: 1.6,
    defaultHeight: 2.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="4"/>
      <rect x="10" y="8" width="36" height="26" rx="12"/>
      <rect x="54" y="8" width="36" height="26" rx="12"/>
      <line x1="5" y1="36" x2="95" y2="36" fill="none"/>
      <line x1="50" y1="36" x2="50" y2="95" fill="none"/>
    `,
  },
  {
    id: "wardrobe",
    label: "Wardrobe",
    category: "bedroom",
    defaultWidth: 2.0,
    defaultHeight: 0.6,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="2"/>
      <line x1="50" y1="5" x2="50" y2="95" fill="none"/>
      <path d="M 50 22 Q 32 35 22 55" fill="none"/>
      <path d="M 50 22 Q 68 35 78 55" fill="none"/>
    `,
  },
  {
    id: "nightstand",
    label: "Nightstand",
    category: "bedroom",
    defaultWidth: 0.5,
    defaultHeight: 0.5,
    svgContent: `
      <rect x="8" y="8" width="84" height="84" rx="4"/>
      <line x1="8" y1="46" x2="92" y2="46" fill="none"/>
      <circle cx="50" cy="27" r="5" fill="none"/>
      <circle cx="50" cy="70" r="5" fill="none"/>
    `,
  },
  {
    id: "desk-bedroom",
    label: "Desk",
    category: "bedroom",
    defaultWidth: 1.2,
    defaultHeight: 0.6,
    svgContent: `
      <rect x="5" y="12" width="90" height="76" rx="3"/>
      <rect x="5" y="78" width="90" height="10" rx="2"/>
    `,
  },
  // ── Kitchen & Dining ─────────────────────────────────────
  {
    id: "dining-table-rect",
    label: "Dining Table",
    category: "kitchen-dining",
    defaultWidth: 1.6,
    defaultHeight: 0.9,
    svgContent: `
      <rect x="10" y="10" width="80" height="80" rx="3"/>
    `,
  },
  {
    id: "dining-table-round",
    label: "Round Table",
    category: "kitchen-dining",
    defaultWidth: 1.2,
    defaultHeight: 1.2,
    svgContent: `
      <circle cx="50" cy="50" r="42"/>
    `,
  },
  {
    id: "dining-chair",
    label: "Dining Chair",
    category: "kitchen-dining",
    defaultWidth: 0.45,
    defaultHeight: 0.45,
    svgContent: `
      <rect x="15" y="32" width="70" height="58" rx="4"/>
      <rect x="15" y="10" width="70" height="24" rx="4"/>
    `,
  },
  {
    id: "kitchen-island",
    label: "Kitchen Island",
    category: "kitchen-dining",
    defaultWidth: 2.0,
    defaultHeight: 1.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="3"/>
      <line x1="5" y1="32" x2="95" y2="32" fill="none"/>
      <circle cx="25" cy="18" r="7" fill="none"/>
      <circle cx="50" cy="18" r="7" fill="none"/>
      <circle cx="75" cy="18" r="7" fill="none"/>
    `,
  },
  {
    id: "fridge",
    label: "Fridge",
    category: "kitchen-dining",
    defaultWidth: 0.7,
    defaultHeight: 0.7,
    svgContent: `
      <rect x="8" y="5" width="84" height="90" rx="5"/>
      <line x1="8" y1="40" x2="92" y2="40" fill="none"/>
      <line x1="22" y1="22" x2="22" y2="37" fill="none" stroke-width="2"/>
      <line x1="22" y1="55" x2="22" y2="90" fill="none" stroke-width="2"/>
    `,
  },
  {
    id: "oven",
    label: "Oven",
    category: "kitchen-dining",
    defaultWidth: 0.6,
    defaultHeight: 0.6,
    svgContent: `
      <rect x="8" y="8" width="84" height="84" rx="4"/>
      <rect x="18" y="16" width="64" height="42" rx="2" fill="none"/>
      <circle cx="30" cy="72" r="8" fill="none"/>
      <circle cx="50" cy="72" r="8" fill="none"/>
      <circle cx="70" cy="72" r="8" fill="none"/>
    `,
  },
  {
    id: "sink-kitchen",
    label: "Kitchen Sink",
    category: "kitchen-dining",
    defaultWidth: 1.0,
    defaultHeight: 0.6,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="3"/>
      <rect x="10" y="12" width="38" height="76" rx="3" fill="none"/>
      <rect x="52" y="12" width="38" height="76" rx="3" fill="none"/>
      <circle cx="29" cy="50" r="5" fill="none"/>
      <circle cx="71" cy="50" r="5" fill="none"/>
    `,
  },
  // ── Bathroom ─────────────────────────────────────────────
  {
    id: "toilet",
    label: "Toilet",
    category: "bathroom",
    defaultWidth: 0.38,
    defaultHeight: 0.7,
    svgContent: `
      <rect x="20" y="5" width="60" height="33" rx="3"/>
      <ellipse cx="50" cy="70" rx="34" ry="28"/>
      <ellipse cx="50" cy="68" rx="26" ry="21" fill="none"/>
    `,
  },
  {
    id: "bathtub",
    label: "Bathtub",
    category: "bathroom",
    defaultWidth: 0.75,
    defaultHeight: 1.7,
    svgContent: `
      <rect x="8" y="5" width="84" height="90" rx="16"/>
      <rect x="15" y="12" width="70" height="76" rx="10" fill="none"/>
      <circle cx="50" cy="22" r="8" fill="none"/>
    `,
  },
  {
    id: "shower",
    label: "Shower",
    category: "bathroom",
    defaultWidth: 0.9,
    defaultHeight: 0.9,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="3"/>
      <line x1="5" y1="5" x2="95" y2="95" fill="none" stroke-dasharray="8 4"/>
      <line x1="95" y1="5" x2="5" y2="95" fill="none" stroke-dasharray="8 4"/>
      <circle cx="50" cy="50" r="12" fill="none"/>
    `,
  },
  {
    id: "sink-basin",
    label: "Sink",
    category: "bathroom",
    defaultWidth: 0.45,
    defaultHeight: 0.55,
    svgContent: `
      <ellipse cx="50" cy="50" rx="42" ry="44"/>
      <ellipse cx="50" cy="50" rx="30" ry="32" fill="none"/>
      <circle cx="50" cy="50" r="5" fill="none"/>
    `,
  },
  // ── Office ───────────────────────────────────────────────
  {
    id: "desk-office",
    label: "Office Desk",
    category: "office",
    defaultWidth: 1.4,
    defaultHeight: 0.7,
    svgContent: `
      <rect x="5" y="18" width="90" height="64" rx="3"/>
      <rect x="5" y="78" width="90" height="14" rx="2"/>
    `,
  },
  {
    id: "office-chair",
    label: "Office Chair",
    category: "office",
    defaultWidth: 0.6,
    defaultHeight: 0.6,
    svgContent: `
      <circle cx="50" cy="50" r="36"/>
      <circle cx="50" cy="50" r="22" fill="none"/>
      <line x1="50" y1="14" x2="50" y2="50" fill="none"/>
    `,
  },
  {
    id: "filing-cabinet",
    label: "Filing Cabinet",
    category: "office",
    defaultWidth: 0.4,
    defaultHeight: 0.6,
    svgContent: `
      <rect x="8" y="5" width="84" height="90" rx="3"/>
      <line x1="8" y1="36" x2="92" y2="36" fill="none"/>
      <line x1="8" y1="67" x2="92" y2="67" fill="none"/>
      <line x1="22" y1="20" x2="22" y2="34" fill="none" stroke-width="2"/>
      <line x1="22" y1="51" x2="22" y2="65" fill="none" stroke-width="2"/>
      <line x1="22" y1="82" x2="22" y2="90" fill="none" stroke-width="2"/>
    `,
  },
  // ── Outdoor ──────────────────────────────────────────────
  {
    id: "garden-table",
    label: "Garden Table",
    category: "outdoor",
    defaultWidth: 1.0,
    defaultHeight: 1.0,
    svgContent: `
      <circle cx="50" cy="50" r="42"/>
      <circle cx="50" cy="50" r="5" fill="none"/>
    `,
  },
  {
    id: "garden-chair",
    label: "Garden Chair",
    category: "outdoor",
    defaultWidth: 0.6,
    defaultHeight: 0.6,
    svgContent: `
      <rect x="14" y="32" width="72" height="58" rx="5"/>
      <rect x="14" y="8" width="72" height="26" rx="5"/>
    `,
  },
  {
    id: "sunlounger",
    label: "Sunlounger",
    category: "outdoor",
    defaultWidth: 0.7,
    defaultHeight: 2.0,
    svgContent: `
      <rect x="10" y="5" width="80" height="75" rx="8"/>
      <rect x="10" y="5" width="80" height="24" rx="8"/>
      <rect x="10" y="82" width="80" height="13" rx="3"/>
    `,
  },
  {
    id: "bbq",
    label: "BBQ",
    category: "outdoor",
    defaultWidth: 0.6,
    defaultHeight: 0.5,
    svgContent: `
      <ellipse cx="50" cy="50" rx="42" ry="38"/>
      <ellipse cx="50" cy="50" rx="30" ry="27" fill="none"/>
      <line x1="8" y1="50" x2="92" y2="50" fill="none"/>
      <line x1="50" y1="12" x2="50" y2="88" fill="none"/>
    `,
  },
  {
    id: "pool-rect",
    label: "Pool (rect)",
    category: "outdoor",
    defaultWidth: 4.0,
    defaultHeight: 8.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="5"/>
      <rect x="13" y="13" width="74" height="74" rx="3" fill="none"/>
      <line x1="13" y1="50" x2="87" y2="50" fill="none" stroke-dasharray="6 3"/>
    `,
  },
  {
    id: "pool-oval",
    label: "Pool (oval)",
    category: "outdoor",
    defaultWidth: 4.0,
    defaultHeight: 6.0,
    svgContent: `
      <ellipse cx="50" cy="50" rx="44" ry="44"/>
      <ellipse cx="50" cy="50" rx="34" ry="34" fill="none"/>
    `,
  },
  {
    id: "hot-tub",
    label: "Hot Tub",
    category: "outdoor",
    defaultWidth: 2.0,
    defaultHeight: 2.0,
    svgContent: `
      <rect x="8" y="8" width="84" height="84" rx="12"/>
      <rect x="16" y="16" width="68" height="68" rx="8" fill="none"/>
      <circle cx="50" cy="50" r="8" fill="none"/>
    `,
  },
  {
    id: "garden-bench",
    label: "Garden Bench",
    category: "outdoor",
    defaultWidth: 0.5,
    defaultHeight: 1.5,
    svgContent: `
      <rect x="8" y="22" width="84" height="56" rx="4"/>
      <line x1="8" y1="44" x2="92" y2="44" fill="none"/>
      <rect x="8" y="5" width="84" height="19" rx="3"/>
    `,
  },
  {
    id: "shed",
    label: "Shed",
    category: "outdoor",
    defaultWidth: 3.0,
    defaultHeight: 2.5,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="2"/>
      <line x1="5" y1="5" x2="50" y2="28" fill="none"/>
      <line x1="95" y1="5" x2="50" y2="28" fill="none"/>
      <rect x="38" y="58" width="24" height="37" rx="1" fill="none"/>
    `,
  },
  // ── Garden ───────────────────────────────────────────────
  {
    id: "tree",
    label: "Tree",
    category: "garden",
    defaultWidth: 1.5,
    defaultHeight: 1.5,
    svgContent: `
      <circle cx="50" cy="50" r="44"/>
      <circle cx="50" cy="50" r="28" fill="none"/>
      <circle cx="50" cy="50" r="6"/>
    `,
  },
  {
    id: "hedge",
    label: "Hedge",
    category: "garden",
    defaultWidth: 0.5,
    defaultHeight: 2.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="8"/>
      <ellipse cx="25" cy="28" rx="18" ry="18" fill="none"/>
      <ellipse cx="50" cy="28" rx="18" ry="18" fill="none"/>
      <ellipse cx="75" cy="28" rx="18" ry="18" fill="none"/>
      <ellipse cx="25" cy="72" rx="18" ry="18" fill="none"/>
      <ellipse cx="50" cy="72" rx="18" ry="18" fill="none"/>
      <ellipse cx="75" cy="72" rx="18" ry="18" fill="none"/>
    `,
  },
  {
    id: "deck-terrace",
    label: "Deck / Terrace",
    category: "garden",
    defaultWidth: 4.0,
    defaultHeight: 3.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="2"/>
      <line x1="5" y1="22" x2="95" y2="22" fill="none"/>
      <line x1="5" y1="39" x2="95" y2="39" fill="none"/>
      <line x1="5" y1="56" x2="95" y2="56" fill="none"/>
      <line x1="5" y1="73" x2="95" y2="73" fill="none"/>
    `,
  },
  {
    id: "car",
    label: "Car",
    category: "garden",
    defaultWidth: 2.0,
    defaultHeight: 4.5,
    svgContent: `
      <rect x="8" y="5" width="84" height="90" rx="12"/>
      <rect x="15" y="18" width="70" height="28" rx="5" fill="none"/>
      <rect x="15" y="62" width="70" height="22" rx="3" fill="none"/>
      <rect x="8" y="8" width="18" height="12" rx="3" fill="none"/>
      <rect x="74" y="8" width="18" height="12" rx="3" fill="none"/>
      <rect x="8" y="78" width="18" height="15" rx="3" fill="none"/>
      <rect x="74" y="78" width="18" height="15" rx="3" fill="none"/>
    `,
  },
  {
    id: "plant",
    label: "Plant",
    category: "garden",
    defaultWidth: 0.4,
    defaultHeight: 0.4,
    svgContent: `
      <circle cx="50" cy="50" r="36"/>
      <circle cx="50" cy="50" r="20" fill="none"/>
      <path d="M 50 22 Q 34 36 34 52" fill="none"/>
      <path d="M 50 22 Q 66 36 66 52" fill="none"/>
    `,
  },
  {
    id: "grass-patch",
    label: "Grass Patch",
    category: "garden",
    defaultWidth: 2.0,
    defaultHeight: 2.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="3"/>
      <line x1="22" y1="5" x2="22" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
      <line x1="39" y1="5" x2="39" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
      <line x1="56" y1="5" x2="56" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
      <line x1="73" y1="5" x2="73" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
    `,
  },
];

export function getTemplate(id: string): FurnitureTemplate | undefined {
  return FURNITURE_TEMPLATES.find((t) => t.id === id);
}
