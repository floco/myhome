from __future__ import annotations

from .models_settings import (
    ConsumableCategory,
    CostCategory,
    InventoryCategory,
    Supplier,
    SettingsDocument,
    WorkCategory,
    _default_consumable_units,
)

# ── Settings: demo-specific category/supplier sets ──────────────────────────
# These are independent of the app's built-in _default_*() lists (used for
# regular homes) so the demo home has enough category variety to spread 30+
# records across meaningfully.

_COST_CATEGORIES = [
    CostCategory(id="cat-fuel", name="Fuel / Heating", emoji="🛢", unit="L", color="#4466cc"),
    CostCategory(id="cat-electricity", name="Electricity", emoji="💡", unit="kWh", color="#44aacc"),
    CostCategory(id="cat-water", name="Water", emoji="💧", unit="m³", color="#44ccaa"),
    CostCategory(id="cat-mortgage", name="Mortgage / Rent", emoji="🏦", unit=None, color="#9966cc"),
    CostCategory(id="cat-insurance", name="Insurance", emoji="🛡", unit=None, color="#cc6699"),
    CostCategory(id="cat-groceries", name="Groceries", emoji="🛒", unit=None, color="#66cc88"),
    CostCategory(id="cat-maintenance", name="Maintenance", emoji="🔧", unit=None, color="#cc8844"),
    CostCategory(id="cat-internet", name="Internet & Phone", emoji="📶", unit=None, color="#4488cc"),
    CostCategory(id="cat-entertainment", name="Entertainment", emoji="🎬", unit=None, color="#aa66cc"),
]

_WORK_CATEGORIES = [
    WorkCategory(id="wcat-plumbing", name="Plumbing", emoji="🔧"),
    WorkCategory(id="wcat-electrical", name="Electrical", emoji="⚡"),
    WorkCategory(id="wcat-roofing", name="Roofing", emoji="🏠"),
    WorkCategory(id="wcat-painting", name="Painting", emoji="🎨"),
    WorkCategory(id="wcat-flooring", name="Flooring", emoji="🪵"),
    WorkCategory(id="wcat-hvac", name="HVAC", emoji="❄️"),
    WorkCategory(id="wcat-landscaping", name="Landscaping", emoji="🌳"),
]

_INVENTORY_CATEGORIES = [
    InventoryCategory(id="inv-electronics", name="Electronics"),
    InventoryCategory(id="inv-appliances", name="Appliances"),
    InventoryCategory(id="inv-furniture", name="Furniture"),
    InventoryCategory(id="inv-tools", name="Tools"),
    InventoryCategory(id="inv-outdoor", name="Outdoor"),
    InventoryCategory(id="inv-bedroom", name="Bedroom"),
    InventoryCategory(id="inv-office", name="Office"),
    InventoryCategory(id="inv-decor", name="Décor"),
]

_CONSUMABLE_CATEGORIES = [
    ConsumableCategory(id="ccat-cleaning", name="Cleaning Supplies", emoji="🧽"),
    ConsumableCategory(id="ccat-kitchen", name="Kitchen Consumables", emoji="🍽️"),
    ConsumableCategory(id="ccat-bathroom", name="Bathroom Supplies", emoji="🧴"),
    ConsumableCategory(id="ccat-filters", name="Filters & Batteries", emoji="🔋"),
    ConsumableCategory(id="ccat-pet", name="Pet Supplies", emoji="🐾"),
    ConsumableCategory(id="ccat-office", name="Office Supplies", emoji="📎"),
]

_SUPPLIERS = [
    Supplier(id="sup-metro-plumbing", name="Metro Plumbing Co."),
    Supplier(id="sup-brightspark-electric", name="BrightSpark Electric"),
    Supplier(id="sup-greenscape-landscaping", name="GreenScape Landscaping"),
    Supplier(id="sup-ace-hardware", name="Ace Hardware"),
    Supplier(id="sup-cleanpro-services", name="CleanPro Services"),
    Supplier(id="sup-valleyview-appliance-repair", name="ValleyView Appliance Repair"),
    Supplier(id="sup-suntrust-roofing", name="SunTrust Roofing"),
    Supplier(id="sup-clearview-window-gutter", name="ClearView Window & Gutter"),
    Supplier(id="sup-home-comfort-hvac", name="Home Comfort HVAC"),
]


def generate_demo_settings() -> SettingsDocument:
    return SettingsDocument(
        costCategories=list(_COST_CATEGORIES),
        workCategories=list(_WORK_CATEGORIES),
        inventoryCategories=list(_INVENTORY_CATEGORIES),
        consumableCategories=list(_CONSUMABLE_CATEGORIES),
        suppliers=list(_SUPPLIERS),
        consumableUnits=_default_consumable_units(),
    )


# ── Chores: (name, emoji, periodDays, room label hint) ──────────────────────
CHORES: list[tuple[str, str, float, str]] = [
    ("Vacuum living room", "🧹", 7, "Living Room"),
    ("Mop kitchen floor", "🧽", 7, "Kitchen"),
    ("Take out trash", "🗑️", 3, "Kitchen"),
    ("Take out recycling", "♻️", 14, "Kitchen"),
    ("Wash bed sheets", "🛏️", 14, "Primary Bedroom"),
    ("Clean bathroom", "🚿", 7, "Bathroom"),
    ("Clean toilets", "🚽", 7, "Bathroom 2"),
    ("Dust furniture", "🪶", 14, "Living Room"),
    ("Wipe kitchen counters", "🧴", 3, "Kitchen"),
    ("Clean refrigerator", "🧊", 30, "Kitchen"),
    ("Clean oven", "🔥", 60, "Kitchen"),
    ("Descale coffee maker", "☕", 30, "Kitchen"),
    ("Clean windows", "🪟", 60, "Living Room"),
    ("Mow lawn", "🌱", 14, "Garage"),
    ("Water houseplants", "🪴", 7, "Living Room"),
    ("Water garden plants", "🌻", 3, "Garage"),
    ("Rake leaves", "🍂", 30, "Garage"),
    ("Trim hedges", "✂️", 45, "Garage"),
    ("Clean gutters", "🍁", 180, "Garage"),
    ("Change HVAC filter", "🌬️", 90, "Laundry Room"),
    ("Test smoke detectors", "🔥", 180, "Living Room"),
    ("Test carbon monoxide detectors", "⚠️", 180, "Living Room"),
    ("Check fire extinguisher", "🧯", 180, "Kitchen"),
    ("Clean dryer lint trap", "🌀", 30, "Laundry Room"),
    ("Deep clean washing machine", "🫧", 60, "Laundry Room"),
    ("Sanitize dishwasher", "🍽️", 60, "Kitchen"),
    ("Organize pantry", "🥫", 60, "Kitchen"),
    ("Organize garage", "🧰", 90, "Garage"),
    ("Wash car", "🚗", 21, "Garage"),
    ("Change car oil", "🛢️", 120, "Garage"),
    ("Sweep porch / entryway", "🧹", 7, "Living Room"),
    ("Clean light fixtures", "💡", 60, "Living Room"),
    ("Wipe down light switches & doorknobs", "🧼", 14, "Living Room"),
    ("Rotate mattress", "🛌", 180, "Primary Bedroom"),
    ("Service HVAC system", "❄️", 180, "Laundry Room"),
]

# ── Inventory: (name, emoji, category id, (min price, max price)) ──────────
INVENTORY_ITEMS: list[tuple[str, str, str, tuple[float, float]]] = [
    ("Samsung 55\" QLED TV", "📺", "inv-electronics", (600, 1200)),
    ("Sony Soundbar", "🔊", "inv-electronics", (150, 400)),
    ("Apple MacBook Pro", "💻", "inv-electronics", (1200, 2500)),
    ("Dell Home Office Monitor", "🖥️", "inv-office", (150, 350)),
    ("HP LaserJet Printer", "🖨️", "inv-office", (100, 250)),
    ("KitchenAid Stand Mixer", "🍰", "inv-appliances", (250, 450)),
    ("Ninja Blender", "🥤", "inv-appliances", (60, 150)),
    ("Breville Espresso Machine", "☕", "inv-appliances", (300, 700)),
    ("Instant Pot", "🍲", "inv-appliances", (70, 150)),
    ("Whirlpool Refrigerator", "🧊", "inv-appliances", (900, 1800)),
    ("Bosch Dishwasher", "🍽️", "inv-appliances", (500, 900)),
    ("LG Washing Machine", "🌀", "inv-appliances", (500, 900)),
    ("Samsung Dryer", "🔥", "inv-appliances", (500, 900)),
    ("IKEA MALM Bed Frame", "🛏️", "inv-bedroom", (150, 350)),
    ("Tempur-Pedic Mattress", "🛌", "inv-bedroom", (800, 2000)),
    ("IKEA PAX Wardrobe", "🚪", "inv-bedroom", (300, 600)),
    ("Nightstand Set", "🕯️", "inv-bedroom", (80, 200)),
    ("Sectional Sofa", "🛋️", "inv-furniture", (800, 2000)),
    ("Dining Table Set", "🍴", "inv-furniture", (400, 1000)),
    ("Bookshelf", "📚", "inv-furniture", (100, 300)),
    ("Coffee Table", "☕", "inv-furniture", (100, 300)),
    ("Office Desk", "🗄️", "inv-office", (150, 400)),
    ("Ergonomic Office Chair", "🪑", "inv-office", (150, 500)),
    ("Dyson V11 Vacuum", "🧹", "inv-tools", (400, 700)),
    ("Cordless Drill Set", "🔩", "inv-tools", (80, 200)),
    ("Ladder", "🪜", "inv-tools", (60, 150)),
    ("Pressure Washer", "💦", "inv-tools", (150, 350)),
    ("Lawn Mower", "🌱", "inv-outdoor", (250, 600)),
    ("Leaf Blower", "🍃", "inv-outdoor", (80, 200)),
    ("Weber Genesis Grill", "🔥", "inv-outdoor", (400, 900)),
    ("Patio Furniture Set", "🪑", "inv-outdoor", (300, 800)),
    ("Garden Shed", "🏚️", "inv-outdoor", (500, 1500)),
    ("Area Rug", "🧵", "inv-decor", (80, 250)),
    ("Wall Art Print Set", "🖼️", "inv-decor", (50, 150)),
    ("Table Lamp Set", "💡", "inv-decor", (40, 120)),
]

# Category id -> preferred room labels (searched on the generated house).
INVENTORY_CATEGORY_ROOM_HINTS: dict[str, list[str]] = {
    "inv-electronics": ["Living Room"],
    "inv-appliances": ["Kitchen"],
    "inv-bedroom": ["Primary Bedroom", "Bedroom 2"],
    "inv-furniture": ["Living Room", "Dining Room"],
    "inv-office": ["Home Office"],
    "inv-tools": ["Garage"],
    "inv-outdoor": ["Garage"],
    "inv-decor": ["Living Room"],
}

CONSUMABLE_CATEGORY_ROOM_HINTS: dict[str, list[str]] = {
    "ccat-cleaning": ["Laundry Room"],
    "ccat-kitchen": ["Kitchen"],
    "ccat-bathroom": ["Bathroom"],
    "ccat-filters": ["Laundry Room"],
    "ccat-pet": ["Kitchen"],
    "ccat-office": ["Home Office"],
}

# ── Works: (title, category id, (min cost, max cost)) ───────────────────────
WORKS: list[tuple[str, str, tuple[float, float]]] = [
    ("Replace water heater", "wcat-plumbing", (800, 1600)),
    ("Fix leaking kitchen faucet", "wcat-plumbing", (100, 300)),
    ("Unclog main sewer line", "wcat-plumbing", (200, 600)),
    ("Repipe upstairs bathroom", "wcat-plumbing", (1500, 3500)),
    ("Install new toilet", "wcat-plumbing", (250, 500)),
    ("Repair garbage disposal", "wcat-plumbing", (100, 250)),
    ("Upgrade electrical panel", "wcat-electrical", (1200, 2500)),
    ("Install ceiling fan", "wcat-electrical", (150, 350)),
    ("Rewire living room outlets", "wcat-electrical", (300, 700)),
    ("Install outdoor security lighting", "wcat-electrical", (200, 500)),
    ("Replace smoke detector wiring", "wcat-electrical", (150, 400)),
    ("Install EV charger", "wcat-electrical", (800, 1800)),
    ("Replace roof shingles (section)", "wcat-roofing", (1500, 4000)),
    ("Repair roof flashing", "wcat-roofing", (300, 800)),
    ("Clean and inspect chimney", "wcat-roofing", (150, 350)),
    ("Install gutter guards", "wcat-roofing", (400, 900)),
    ("Repaint living room", "wcat-painting", (300, 800)),
    ("Repaint exterior siding", "wcat-painting", (2000, 5000)),
    ("Paint kitchen cabinets", "wcat-painting", (500, 1200)),
    ("Touch up trim and baseboards", "wcat-painting", (100, 300)),
    ("Refinish hardwood floors", "wcat-flooring", (1500, 3500)),
    ("Install new carpet in bedroom", "wcat-flooring", (600, 1400)),
    ("Repair damaged tile in bathroom", "wcat-flooring", (200, 500)),
    ("Install laminate flooring in office", "wcat-flooring", (800, 1800)),
    ("Service HVAC system", "wcat-hvac", (150, 350)),
    ("Replace furnace", "wcat-hvac", (2500, 5500)),
    ("Install smart thermostat", "wcat-hvac", (150, 350)),
    ("Duct cleaning", "wcat-hvac", (300, 600)),
    ("Repair air conditioning unit", "wcat-hvac", (200, 600)),
    ("Landscape front yard", "wcat-landscaping", (800, 2500)),
    ("Install sprinkler system", "wcat-landscaping", (1500, 3500)),
    ("Trim large trees", "wcat-landscaping", (300, 800)),
    ("Build backyard deck", "wcat-landscaping", (3000, 8000)),
    ("Repair fence panel", "wcat-landscaping", (150, 400)),
    ("Install garden retaining wall", "wcat-landscaping", (800, 2000)),
]

# ── Knowledge Base: titles ───────────────────────────────────────────────────
KB_TITLES: list[str] = [
    "Furnace Filter Replacement Guide",
    "Wi-Fi Router Reset Instructions",
    "Water Shutoff Valve Location",
    "Main Electrical Panel Location & Breaker Map",
    "Trash & Recycling Pickup Schedule",
    "Home Alarm System Codes (keep private)",
    "Emergency Contact List",
    "Warranty Contacts & Reference Numbers",
    "Appliance Manuals — Where to Find Them",
    "HVAC System Maintenance Schedule",
    "Smoke & CO Detector Battery Replacement Log",
    "Garage Door Opener Remote Programming",
    "Septic Tank Service History",
    "Well Water Testing Schedule",
    "Gas Shutoff Valve Location",
    "Circuit Breaker Labeling Reference",
    "Paint Colors Reference (by room)",
    "Flooring Materials Reference",
    "Home Insurance Policy Summary",
    "Property Tax Payment Schedule",
    "Home Security Camera Access Instructions",
    "Guest Wi-Fi Password Instructions",
    "Sprinkler System Zone Map",
    "Pool / Spa Maintenance Checklist",
    "Snow Removal Contractor Info",
    "Lawn Care Schedule",
    "Pest Control Service History",
    "Chimney Sweep Service History",
    "Roof Inspection Notes",
    "Window & Door Weatherproofing Notes",
    "Moving-In Checklist",
    "Utility Provider Contacts",
    "HOA Rules & Contact Info",
    "Recommended Local Contractors",
    "Home Inventory for Insurance Claims",
]

KB_OPENERS: list[str] = [
    "Keep this reference up to date so anyone in the household can find it quickly.",
    "Written down here so it doesn't get lost in a drawer somewhere.",
    "Update this whenever something changes so it stays accurate.",
    "A quick reference for future-you, or whoever's dealing with this next.",
]

KB_CLOSERS: list[str] = [
    "Double-check details in person before relying on this for anything urgent.",
    "If anything here goes out of date, update it the same day you notice.",
    "Ask a neighbor or the previous owner if any of this seems unclear.",
    "Cross-reference with the relevant manual or provider website if unsure.",
]

# ── Consumables: (name, emoji, category id, unit) ────────────────────────────
CONSUMABLES: list[tuple[str, str, str, str]] = [
    ("Paper Towels", "🧻", "ccat-cleaning", "rolls"),
    ("Dish Soap", "🧴", "ccat-kitchen", "L"),
    ("Laundry Detergent", "🧺", "ccat-cleaning", "L"),
    ("Fabric Softener", "🌸", "ccat-cleaning", "L"),
    ("All-Purpose Cleaner", "🧽", "ccat-cleaning", "L"),
    ("Glass Cleaner", "🪟", "ccat-cleaning", "L"),
    ("Toilet Bowl Cleaner", "🚽", "ccat-bathroom", "count"),
    ("Bathroom Bleach", "🧴", "ccat-bathroom", "L"),
    ("Sponges", "🧽", "ccat-kitchen", "count"),
    ("Trash Bags", "🗑️", "ccat-cleaning", "rolls"),
    ("Recycling Bags", "♻️", "ccat-cleaning", "rolls"),
    ("Toilet Paper", "🧻", "ccat-bathroom", "rolls"),
    ("Facial Tissues", "🤧", "ccat-bathroom", "count"),
    ("Hand Soap", "🧼", "ccat-bathroom", "count"),
    ("Shampoo", "🧴", "ccat-bathroom", "count"),
    ("Conditioner", "🧴", "ccat-bathroom", "count"),
    ("Toothpaste", "🪥", "ccat-bathroom", "count"),
    ("HVAC Filter 16x20", "🌬️", "ccat-filters", "count"),
    ("Water Filter Cartridge", "💧", "ccat-filters", "count"),
    ("Vacuum Bags", "🧹", "ccat-cleaning", "count"),
    ("AA Batteries", "🔋", "ccat-filters", "count"),
    ("AAA Batteries", "🔋", "ccat-filters", "count"),
    ("9V Batteries", "🔋", "ccat-filters", "count"),
    ("Light Bulbs (LED)", "💡", "ccat-filters", "count"),
    ("Coffee Pods", "☕", "ccat-kitchen", "count"),
    ("Ground Coffee", "☕", "ccat-kitchen", "kg"),
    ("Dishwasher Pods", "🍽️", "ccat-kitchen", "count"),
    ("Aluminum Foil", "🧴", "ccat-kitchen", "count"),
    ("Plastic Wrap", "🧴", "ccat-kitchen", "count"),
    ("Ziplock Bags", "🧴", "ccat-kitchen", "count"),
    ("Dog Food", "🐕", "ccat-pet", "kg"),
    ("Cat Litter", "🐈", "ccat-pet", "kg"),
    ("Printer Paper", "📄", "ccat-office", "packs"),
    ("Printer Ink Cartridges", "🖨️", "ccat-office", "count"),
    ("Sticky Notes", "📝", "ccat-office", "packs"),
]
