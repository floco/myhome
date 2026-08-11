<script lang="ts">
  import { _ } from "svelte-i18n";
  import { untrack } from "svelte";
  import type { Point, WallType } from "@myhome/geometry";
  import { pointsEqual, findAdjacentRooms } from "@myhome/geometry";
  import { createHouseStore } from "./lib/houseStore.svelte";
  import { createViewportStore } from "./lib/viewportStore.svelte";
  import { createToolStore, type ToolType } from "./lib/toolStore.svelte";
  import { createFloatingDrag } from "./lib/floatingDrag.svelte";
  import { createHaStateStore } from "./lib/haStateStore.svelte";
  import { placePoint, allEndpoints } from "./lib/drawingTool";
  import { findSnapPoint, snapToGrid, SNAP_RADIUS_PX, hitTestWall, HIT_RADIUS_PX } from "./lib/geometry-helpers";
  import type { Opening } from "@myhome/geometry";
  import Canvas from "./lib/components/Canvas.svelte";
  import RoomPanel from "./lib/components/RoomPanel.svelte";
  import OpeningPanel from "./lib/components/OpeningPanel.svelte";
  import FloorSwitcher from "./lib/components/FloorSwitcher.svelte";
  import { createChoreStore } from "./lib/choreStore.svelte";
  import type { Assignment } from "./lib/choreStore.svelte";
  import ChoreOverlay from "./lib/components/ChoreOverlay.svelte";
  import ItemPickerPanel from "./lib/components/ItemPickerPanel.svelte";
  import type { PickerLayer } from "./lib/components/ItemPickerPanel.svelte";
  import BadgePopup from "./lib/components/BadgePopup.svelte";
  import ChoresPage from "./lib/components/ChoresPage.svelte";
  import NavMenu from "./lib/components/NavMenu.svelte";
  import HomePage from "./lib/components/HomePage.svelte";
  import NewChoreModal from "./lib/components/NewChoreModal.svelte";
  import LayersDropdown from "./lib/components/LayersDropdown.svelte";
  import InventoryPage from "./lib/components/InventoryPage.svelte";
  import ConsumablesPage from "./lib/components/ConsumablesPage.svelte";
  import { createConsumableStore } from "./lib/consumableStore.svelte";
  import type { Consumable } from "./lib/consumableStore.svelte";
  import LocationsPage from "./lib/components/LocationsPage.svelte";
  import { createLocationsStore } from "./lib/locationsStore.svelte";
  import PropertiesPage from "./lib/components/PropertiesPage.svelte";
  import { createPropertiesStore } from "./lib/propertiesStore.svelte";
  import BuildPage from "./lib/components/BuildPage.svelte";
  import TaskModal from "./lib/components/TaskModal.svelte";
  import { createBuildStore } from "./lib/buildStore.svelte";
  import ContactsPage from "./lib/components/ContactsPage.svelte";
  import { createContactsStore } from "./lib/contactsStore.svelte";
  import InsurancePage from "./lib/components/InsurancePage.svelte";
  import { createInsuranceStore } from "./lib/insuranceStore.svelte";
  import { createNotificationStore } from "./lib/notificationStore.svelte";
  import type { Notification } from "./lib/notificationStore.svelte";
  import NotificationBell from "./lib/components/NotificationBell.svelte";
  import ConsumableOverlay from "./lib/components/ConsumableOverlay.svelte";
  import ConsumablePinPopup from "./lib/components/ConsumablePinPopup.svelte";
  import WorksPage from "./lib/components/WorksPage.svelte";
  import { createInventoryStore } from "./lib/inventoryStore.svelte";
  import type { InventoryItem } from "./lib/inventoryStore.svelte";
  import InventoryOverlay from "./lib/components/InventoryOverlay.svelte";
  import InventoryPinPopup from "./lib/components/InventoryPinPopup.svelte";
  import { createSettingsStore } from "./lib/settingsStore.svelte";
  import SettingsPage from "./lib/components/SettingsPage.svelte";
  import { createCostsStore } from "./lib/costsStore.svelte";
  import CostsPage from "./lib/components/CostsPage.svelte";
  import CostsOverlay from "./lib/components/CostsOverlay.svelte";
  import CostsPinPopup from "./lib/components/CostsPinPopup.svelte";
  import type { CostCategory } from "./lib/settingsStore.svelte";
  import { createWorksStore } from "./lib/worksStore.svelte";
  import type { Work } from "./lib/worksStore.svelte";
  import WorksOverlay from "./lib/components/WorksOverlay.svelte";
  import WorksPinPopup from "./lib/components/WorksPinPopup.svelte";
  import { createKBStore } from "./lib/kbStore.svelte";
  import KBPage from "./lib/components/KBPage.svelte";
  import { createGuardedHashRouter } from "./lib/navGuard";
  import { getStoredTheme, toggleTheme, type Theme } from "./lib/theme";
  import { createAuthStore } from "./lib/authStore.svelte";
  import LoginPage from "./lib/components/LoginPage.svelte";
  import Modal from "./lib/components/ui/Modal.svelte";
  import Popover from "./lib/components/ui/Popover.svelte";
  import Input from "./lib/components/ui/Input.svelte";
  import Button from "./lib/components/ui/Button.svelte";
  import { homesStore } from "./lib/homesStore.svelte";
  import NewHomeModal from "./lib/components/NewHomeModal.svelte";
  import HomesSwitcher from "./lib/components/HomesSwitcher.svelte";
  import FurnitureLibraryPanel from "./lib/components/FurnitureLibraryPanel.svelte";
  import FurnitureParamsPanel from "./lib/components/FurnitureParamsPanel.svelte";
  import { getTemplate } from "./lib/furnitureLibrary";
  import CommandPalette from "./lib/components/CommandPalette.svelte";
  import { buildSearchIndex, type SearchResult } from "./lib/searchIndex";

  const getHomeId = () => homesStore.activeHomeId;

  const floorStore = createHouseStore(getHomeId);
  const viewportStore = createViewportStore();
  const toolStore = createToolStore();
  const choreStore = createChoreStore(getHomeId);
  const inventoryStore = createInventoryStore(getHomeId);
  const settingsStore = createSettingsStore(getHomeId);
  const costsStore = createCostsStore(getHomeId);
  const worksStore = createWorksStore(getHomeId);
  const kbStore = createKBStore(getHomeId);
  const consumableStore = createConsumableStore(getHomeId);
  const locationsStore = createLocationsStore(getHomeId);
  const propertiesStore = createPropertiesStore(getHomeId);
  const buildStore = createBuildStore(getHomeId);
  const contactsStore = createContactsStore(getHomeId);
  const insuranceStore = createInsuranceStore(getHomeId);
  const notificationStore = createNotificationStore(getHomeId);
  const authStore = createAuthStore();

  $effect(() => {
    if (authStore.user) {
      homesStore.loadHomes();
    } else if (!authStore.checking) {
      homesStore._reset();
    }
  });

  function reloadAllStores(): void {
    floorStore.reload();
    choreStore.reload();
    inventoryStore.reload();
    settingsStore.reload();
    costsStore.reload();
    worksStore.reload();
    kbStore.reload();
    consumableStore.reload();
    locationsStore.reload();
    propertiesStore.reload();
    buildStore.reload();
    contactsStore.reload();
    insuranceStore.reload();
    notificationStore.reload();
  }

  $effect(() => {
    const _homeId = homesStore.activeHomeId;
    reloadAllStores();
  });

  let theme = $state<Theme>(getStoredTheme());
  function handleToggleTheme(): void {
    theme = toggleTheme(theme);
  }

  let selectedInventoryPin = $state<{
    item: InventoryItem;
    screenX: number;
    screenY: number;
  } | null>(null);
  let selectedInventoryItemId = $state<string | null>(null);
  let draggingItemId = $state<string | null>(null);
  let draggingLayerId = $state<string | null>(null);
  let pickerHighlightId = $state<string | null>(null);
  let pointerDragFurnitureTemplateId = $state<string | null>(null);
  let dragGhost = $state<{ x: number; y: number; emoji: string; label: string } | null>(null);
  let furniturePointerDownAt: { x: number; y: number } | null = null;

  let commandPaletteOpen = $state(false);
  let selectedChoreId = $state<string | null>(null);
  let selectedConsumableId = $state<string | null>(null);
  let selectedWorkId = $state<string | null>(null);
  let openBuildTaskId = $state<string | null>(null);
  let selectedCostEntryId = $state<string | null>(null);

  const globalSearchIndex = $derived(buildSearchIndex({
    choreStore, inventoryStore, consumableStore, worksStore, costsStore, kbStore, settingsStore, contactsStore,
  }));

  function handleSearchSelect(result: SearchResult): void {
    commandPaletteOpen = false;
    if (result.module === "chores") { selectedChoreId = result.id; window.location.hash = "#/chores"; }
    else if (result.module === "inventory") { selectedInventoryItemId = result.id; window.location.hash = "#/inventory"; }
    else if (result.module === "consumables") { selectedConsumableId = result.id; window.location.hash = "#/consumables"; }
    else if (result.module === "works") { selectedWorkId = result.id; window.location.hash = "#/works"; }
    else if (result.module === "costs") { selectedCostEntryId = result.id; window.location.hash = "#/costs"; }
    else if (result.module === "kb") { window.location.hash = "#/kb/" + encodeURIComponent(result.id); }
  }

  function handleNotificationSelect(n: Notification): void {
    if (n.type === "chore") { selectedChoreId = n.refId; window.location.hash = "#/chores"; }
    else if (n.type === "low_stock") { selectedConsumableId = n.refId; window.location.hash = "#/consumables"; }
    else if (n.type === "warranty") { selectedInventoryItemId = n.refId; window.location.hash = "#/inventory"; }
  }

  let selectedCostCategoryPin = $state<{
    category: CostCategory;
    screenX: number;
    screenY: number;
  } | null>(null);
  let selectedConsumablePin = $state<{
    consumable: Consumable;
    screenX: number;
    screenY: number;
  } | null>(null);
  let selectedWorkPin = $state<{
    work: Work;
    screenX: number;
    screenY: number;
  } | null>(null);

  let activeLayers = $state(new Set<string>(["ha"]));
  const choreLayerActive = $derived(activeLayers.has("chores"));
  const inventoryLayerActive = $derived(activeLayers.has("inventory"));
  const costsLayerActive = $derived(activeLayers.has("costs"));
  const currentFloorCostCategories = $derived(
    settingsStore.costCategories.filter(c => c.placement?.floorId === floorStore.currentFloorId)
  );
  const worksLayerActive = $derived(activeLayers.has("works"));
  const consumablesLayerActive = $derived(activeLayers.has("consumables"));
  const haLayerActive = $derived(activeLayers.has("ha"));
  const currentFloorConsumables = $derived(
    consumableStore.consumables.filter(c => c.placement?.floorId === floorStore.currentFloorId)
  );
  const consumablesPickerLayer = $derived<PickerLayer>({
    id: "consumables",
    label: $_('common.modules.consumables'),
    emoji: "🛒",
    items: consumableStore.consumables.map(c => ({
      id: c.id,
      name: c.name,
      emoji: c.emoji,
      placed: c.placement !== null,
    })),
  });
  const currentFloorWorks = $derived(
    worksStore.works.filter(w => w.placement?.floorId === floorStore.currentFloorId)
  );
  const worksPickerLayer = $derived<PickerLayer>({
    id: "works",
    label: $_('common.modules.works'),
    emoji: "🔧",
    items: worksStore.works.map(w => ({
      id: w.id,
      name: w.title,
      emoji: w.categoryId
        ? (settingsStore.workCategories.find(c => c.id === w.categoryId)?.emoji ?? "🔧")
        : "🔧",
      placed: w.placement !== null,
    })),
  });

  function choreDisplayName(name: string, emoji: string): string {
    const trimmed = name.trim();
    return (emoji && trimmed.startsWith(emoji)) ? trimmed.slice(emoji.length).trim() : trimmed;
  }

  const chorePickerLayer = $derived<PickerLayer>({
    id: "chores",
    label: $_('common.modules.chores'),
    emoji: "✅",
    items: choreStore.chores.map(c => ({
      id: c.id,
      name: choreDisplayName(c.name, c.emoji),
      emoji: c.emoji,
      placed: choreStore.assignments.some(a => a.choreId === c.id),
    })),
  });

  const inventoryPickerLayer = $derived<PickerLayer>({
    id: "inventory",
    label: $_('common.modules.inventory'),
    emoji: "📦",
    items: inventoryStore.items.map(i => ({
      id: i.id,
      name: i.name,
      emoji: i.emoji,
      placed: i.placement !== null,
    })),
  });

  const costsPickerLayer = $derived<PickerLayer>({
    id: "costs",
    label: $_('common.modules.costs'),
    emoji: "💰",
    items: settingsStore.costCategories.map(c => ({
      id: c.id,
      name: c.name,
      emoji: c.emoji,
      placed: c.placement?.floorId === floorStore.currentFloorId,
    })),
  });

  const pickerLayers = $derived<PickerLayer[]>([
    ...(choreLayerActive ? [chorePickerLayer] : []),
    ...(inventoryLayerActive ? [inventoryPickerLayer] : []),
    ...(consumablesLayerActive ? [consumablesPickerLayer] : []),
    ...(costsLayerActive ? [costsPickerLayer] : []),
    ...(worksLayerActive ? [worksPickerLayer] : []),
  ]);

  function toggleLayer(layer: string): void {
    const next = new Set(activeLayers);
    if (next.has(layer)) next.delete(layer);
    else next.add(layer);
    activeLayers = next;
    if (next.has("chores")) toolStore.setTool("select");
  }

  let selectedBadge = $state<{ assignment: Assignment; screenX: number; screenY: number } | null>(null);

  $effect(() => {
    if (!choreLayerActive) selectedBadge = null;
  });
  let pickerOpen = $state(false);
  const ALL_FLOOR_ID = "__all__";
  const TOOL_ICONS: Record<ToolType, string> = {
    pan: "✋",
    select: "🖱",
    wall: "🧱",
    divider: "╌",
    garden: "🌿",
    door: "🚪",
    window: "🪟",
  };
  let allFloorsMode = $state(false);
  let viewMode = $state(false);
  let openGroup = $state<"view" | "draw" | "actions" | null>(null);
  let viewTriggerEl = $state<HTMLButtonElement | null>(null);
  let drawTriggerEl = $state<HTMLButtonElement | null>(null);
  let actionsTriggerEl = $state<HTMLButtonElement | null>(null);

  function toggleViewMode(): void {
    viewMode = !viewMode;
    openGroup = null;
    if (viewMode) {
      toolStore.setTool("select");
      pickerOpen = false;
      furnitureLibraryOpen = false;
    }
  }
  const ftDrag = createFloatingDrag(".floating-toolbar");
  const fpDrag = createFloatingDrag(".furniture-float");
  const ipDrag = createFloatingDrag(".picker-float");
  const rpDrag = createFloatingDrag(".room-panel-float");
  const opDrag = createFloatingDrag(".opening-panel-float");
  const fpanelDrag = createFloatingDrag(".furniture-params-panel-float");
  const haStateStore = createHaStateStore();
  let navExpanded = $state(false);
  let showNewChoreModal = $state(false);
  let userMenuOpen = $state(false);
  let showChangePassword = $state(false);
  let cpCurrent = $state("");
  let cpNew = $state("");
  let cpError = $state<string | null>(null);
  let cpLoading = $state(false);

  async function handleChangePassword(): Promise<void> {
    cpError = null;
    cpLoading = true;
    try {
      await authStore.changePassword(cpCurrent, cpNew);
      showChangePassword = false;
      cpCurrent = "";
      cpNew = "";
    } catch (e) {
      cpError = e instanceof Error ? e.message : $_('app.changePassword.failed');
    } finally {
      cpLoading = false;
    }
  }

  async function handleSignOut(): Promise<void> {
    await authStore.logout();
    userMenuOpen = false;
  }

  let currentRoute = $state(window.location.hash || "#/");
  const hashRouter = createGuardedHashRouter({
    getHash: () => window.location.hash || "#/",
    setHash: (hash) => { window.location.hash = hash; },
    onRoute: (hash) => { currentRoute = hash; },
  });
  $effect(() => {
    window.addEventListener("hashchange", hashRouter.handleHashChange);
    return () => window.removeEventListener("hashchange", hashRouter.handleHashChange);
  });

  const isFloorPlan = $derived(currentRoute === "#/plan");
  const isHome = $derived(currentRoute === "#/" || currentRoute === "");
  const kbRouteId = $derived(
    currentRoute.startsWith("#/kb/") ? decodeURIComponent(currentRoute.slice("#/kb/".length)) : null,
  );

  const selectedRoom = $derived(
    toolStore.state.selectedRoomId
      ? (floorStore.floor.rooms.find((r) => r.id === toolStore.state.selectedRoomId) ?? null)
      : null
  );

  const selectedOpening = $derived(
    toolStore.state.selectedOpeningId
      ? (floorStore.floor.openings.find((o) => o.id === toolStore.state.selectedOpeningId) ?? null)
      : null
  );
  const selectedOpeningWall = $derived(
    selectedOpening
      ? (floorStore.floor.walls.find((w) => w.id === selectedOpening.wallId) ?? null)
      : null
  );
  const selectedOpeningAreaIds = $derived.by(() => {
    if (!selectedOpening || !selectedOpeningWall) return [];
    const rooms = findAdjacentRooms(selectedOpening, selectedOpeningWall, floorStore.floor.rooms);
    return [...new Set(rooms.map((r) => r.haAreaId).filter((id): id is string => id !== null))];
  });

  const currentFloorRoomIds = $derived(new Set(floorStore.floor.rooms.map((r) => r.id)));
  const currentFloorAssignments = $derived(
    choreStore.assignments.filter((a) => a.roomId !== null && currentFloorRoomIds.has(a.roomId))
  );
  const currentFloorInventoryItems = $derived(
    inventoryStore.items.filter(
      (i) => i.placement?.floorId === floorStore.currentFloorId
    )
  );

  let spacePressed = $state(false);
  let canvasWidth = $state(1200);
  let canvasHeight = $state(800);
  let saveStatus = $state<"idle" | "saving" | "saved" | "error">("idle");

  $effect(() => {
    const _currentFloorId = floorStore.currentFloorId;
    const isLoaded = floorStore.loaded;
    if (!isLoaded) return;
    untrack(() => {
      // An empty floor (nothing drawn yet, or the transient placeholder
      // shown before a home's data has loaded) has nothing to fit to —
      // leave the viewport as-is rather than recentering to a meaningless
      // {width/2, height/2} point.
      if (canvasWidth > 0 && canvasHeight > 0 && floorStore.floor.walls.length > 0) {
        viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight);
      }
    });
  });

  // Furniture state
  let furnitureLibraryOpen = $state(false);
  let selectedFurnitureId = $state<string | null>(null);
  const selectedFurnitureObject = $derived(
    selectedFurnitureId
      ? (floorStore.currentFurniture.find((f) => f.id === selectedFurnitureId) ?? null)
      : null
  );
  const selectedFurnitureTemplate = $derived(
    selectedFurnitureObject ? (getTemplate(selectedFurnitureObject.templateId) ?? null) : null
  );

  interface FurnitureDragMove {
    type: "move"; id: string;
    startObjX: number; startObjY: number;
    startCursorX: number; startCursorY: number;
  }
  interface FurnitureDragResize {
    type: "resize"; id: string;
    fixedX: number; fixedY: number;
    rotation: number;
  }
  interface FurnitureDragRotate {
    type: "rotate"; id: string;
    cx: number; cy: number;
  }
  type FurnitureDrag = FurnitureDragMove | FurnitureDragResize | FurnitureDragRotate;
  let furnitureDrag = $state<FurnitureDrag | null>(null);
  let haAreas = $state<Array<{ area_id: string; name: string }>>([]);

  const hasSelection = $derived(
    toolStore.state.selectedId !== null || toolStore.state.selectedOpeningId !== null || selectedFurnitureId !== null
  );
  const saveIcon = $derived(
    saveStatus === "saving" ? "⋯" : saveStatus === "saved" ? "✓" : saveStatus === "error" ? "⚠" : "💾"
  );
  const saveTitle = $derived(
    saveStatus === "saving" ? $_('settings.security.saving') : saveStatus === "saved" ? $_('app.floatingToolbar.saved') : saveStatus === "error" ? $_('app.floatingToolbar.saveError', { values: { detail: saveError ? ": " + saveError : "" } }) : $_('common.save')
  );

  let saveError = $state<string | null>(null);

  async function handleSave(): Promise<void> {
    saveStatus = "saving";
    saveError = null;
    try {
      await floorStore.save();
      saveStatus = "saved";
      setTimeout(() => { saveStatus = "idle"; }, 2000);
    } catch (e) {
      saveError = e instanceof Error ? e.message : String(e);
      saveStatus = "error";
      setTimeout(() => { saveStatus = "idle"; }, 4000);
    }
  }

  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    const _gen = floorStore.generation;
    if (!floorStore.loaded || !floorStore.isDirty || !homesStore.activeHomeId) return;
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => {
      autosaveTimer = null;
      handleSave();
    }, 5000);
    return () => {
      if (autosaveTimer) { clearTimeout(autosaveTimer); autosaveTimer = null; }
    };
  });

  $effect(() => {
    fetch("/api/ha/areas")
      .then((r) => r.json())
      .then((areas: Array<{ area_id: string; name: string }>) => { haAreas = areas; })
      .catch(() => { haAreas = []; });
  });

  $effect(() => {
    haStateStore.setActive(isFloorPlan && haLayerActive);
  });

  $effect(() => {
    const ids = new Set<string>();
    for (const opening of floorStore.floor.openings) {
      if (opening.haEntityId) ids.add(opening.haEntityId);
      if (opening.hasShutter && opening.shutterEntityId) ids.add(opening.shutterEntityId);
    }
    haStateStore.setEntityIds(ids);
  });

  function handleSelect(id: string | null): void {
    if (toolStore.state.tool === "select") toolStore.select(id);
  }

  function handleSelectOpening(id: string | null): void { toolStore.selectOpening(id); }
  function handleSelectRoom(id: string | null): void { toolStore.selectRoom(id); }

  function handleBadgeClick(assignmentId: string): void {
    const assignment = choreStore.assignments.find((a) => a.id === assignmentId);
    if (!assignment) return;
    let screenX = 0, screenY = 0;
    if (assignment.position) {
      const sp = viewportStore.worldToScreen(assignment.position);
      screenX = sp.x; screenY = sp.y;
    }
    selectedBadge = { assignment, screenX, screenY };
  }

  function handleBadgeDragEnd(assignmentId: string, worldPos: { x: number; y: number }): void {
    choreStore.updateAssignmentPosition(assignmentId, worldPos);
  }

  function handleDelete(): void {
    if (selectedFurnitureId) {
      floorStore.removeFurniture(selectedFurnitureId);
      selectedFurnitureId = null;
      return;
    }
    const { selectedId, selectedOpeningId } = toolStore.state;
    if (selectedId) { floorStore.removeWall(selectedId); toolStore.select(null); }
    else if (selectedOpeningId) { floorStore.removeOpening(selectedOpeningId); toolStore.selectOpening(null); }
  }

  function handleUndo(): void {
    floorStore.undo(); toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null); selectedFurnitureId = null;
  }

  function handleRedo(): void {
    floorStore.redo(); toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null); selectedFurnitureId = null;
  }

  function wouldCollapseAWall(dragging: Point, snapped: Point): boolean {
    return floorStore.floor.walls.some(
      (w) =>
        (pointsEqual(w.start, dragging) && pointsEqual(w.end, snapped)) ||
        (pointsEqual(w.end, dragging) && pointsEqual(w.start, snapped)),
    );
  }

  function handleDragMove(worldCursor: Point): void {
    const dragging = toolStore.state.draggingPoint;
    if (!dragging) return;
    const candidates = allEndpoints(floorStore.floor.walls).filter((p) => !pointsEqual(p, dragging));
    const snapRadiusWorld = SNAP_RADIUS_PX / viewportStore.viewport.zoom;
    const snapped = findSnapPoint(worldCursor, candidates, snapRadiusWorld) ?? snapToGrid(worldCursor);
    if (pointsEqual(snapped, dragging)) return;
    if (wouldCollapseAWall(dragging, snapped)) return;
    floorStore.moveSharedPoint(dragging, snapped, { skipHistory: true });
    toolStore.updateDragPoint(snapped);
  }

  function handlePointerMove(world: Point): void {
    toolStore.setCursor(world);
    if (toolStore.state.draggingPoint) handleDragMove(world);
    if (toolStore.state.draggingOpeningHandle) handleOpeningHandleDrag(world);
    if (furnitureDrag) handleFurnitureDragMove(world);
  }

  function handleOpeningPlace(worldCursor: Point): void {
    const thresholdWorld = HIT_RADIUS_PX / viewportStore.viewport.zoom;
    const hit = hitTestWall(worldCursor, floorStore.floor.walls, thresholdWorld);
    if (!hit) return;
    const { wall, offset } = hit;
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const wallLength = Math.hypot(dx, dy);
    const tool = toolStore.state.tool;
    const defaultWidth = tool === "door" ? 0.9 : 1.2;
    const width = Math.min(defaultWidth, wallLength - offset);
    if (width < 1e-9) return;
    const openingEnd = offset + width;
    if (floorStore.openingOverlaps(wall.id, null, offset, openingEnd)) return;
    const opening: Opening = {
      id: crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36),
      wallId: wall.id, type: tool as "door" | "window", offset, width,
      ...(tool === "door" ? { swing: "left-in" as const } : {}),
    };
    floorStore.addOpening(opening);
  }

  function handlePlacePoint(point: Point): void {
    const tool = toolStore.state.tool;
    if (tool === "door" || tool === "window") { handleOpeningPlace(point); return; }
    if (tool === "select") return;
    const chain = toolStore.state.drawPoints;
    if (chain.length === 0) { toolStore.addDrawPoint(point); return; }
    const { segment, chainEnds } = placePoint(chain, point, tool as WallType, () =>
      crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36),
    );
    if (segment) { floorStore.addWall(segment); toolStore.addDrawPoint(point); }
    if (chainEnds) toolStore.resetDraw();
  }

  function handleDragStart(point: Point): void { floorStore.saveSnapshot(); toolStore.startDrag(point); }
  function handleDragEnd(): void { toolStore.endDrag(); }

  function handleSelectFurniture(id: string | null): void {
    selectedFurnitureId = id;
  }

  function handleMoveFurnitureStart(id: string, e: PointerEvent): void {
    const obj = floorStore.currentFurniture.find((f) => f.id === id);
    if (!obj) return;
    floorStore.saveSnapshot();
    // e.target is an SVG child element; ownerSVGElement gives the root <svg>
    const svgEl = (e.target as SVGElement).ownerSVGElement;
    if (!svgEl) return;
    const svgRect = svgEl.getBoundingClientRect();
    const cursorX = (e.clientX - svgRect.left - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
    const cursorY = (e.clientY - svgRect.top - viewportStore.viewport.panY) / viewportStore.viewport.zoom;
    furnitureDrag = { type: "move", id, startObjX: obj.x, startObjY: obj.y, startCursorX: cursorX, startCursorY: cursorY };
  }

  function handleResizeFurnitureStart(id: string, corner: string, _e: PointerEvent): void {
    const obj = floorStore.currentFurniture.find((f) => f.id === id);
    if (!obj) return;
    floorStore.saveSnapshot();
    const rad = (obj.rotation * Math.PI) / 180;
    const cosR = Math.cos(rad), sinR = Math.sin(rad);
    const hw = obj.width / 2, hh = obj.height / 2;
    // Fixed corner offset (opposite of dragged corner)
    const opp: Record<string, [number, number]> = { nw: [hw, hh], ne: [-hw, hh], se: [-hw, -hh], sw: [hw, -hh] };
    const [lx, ly] = opp[corner] ?? [hw, hh];
    const fixedX = obj.x + lx * cosR - ly * sinR;
    const fixedY = obj.y + lx * sinR + ly * cosR;
    furnitureDrag = { type: "resize", id, fixedX, fixedY, rotation: obj.rotation };
  }

  function handleRotateFurnitureStart(id: string, _e: PointerEvent): void {
    const obj = floorStore.currentFurniture.find((f) => f.id === id);
    if (!obj) return;
    floorStore.saveSnapshot();
    furnitureDrag = { type: "rotate", id, cx: obj.x, cy: obj.y };
  }

  function handleFurnitureDragMove(world: Point): void {
    if (!furnitureDrag) return;
    if (furnitureDrag.type === "move") {
      const dx = world.x - furnitureDrag.startCursorX;
      const dy = world.y - furnitureDrag.startCursorY;
      floorStore.moveFurniture(furnitureDrag.id, furnitureDrag.startObjX + dx, furnitureDrag.startObjY + dy, { skipHistory: true });
    } else if (furnitureDrag.type === "resize") {
      const { fixedX, fixedY, rotation } = furnitureDrag;
      const rad = (rotation * Math.PI) / 180;
      const cosR = Math.cos(rad), sinR = Math.sin(rad);
      const diffX = world.x - fixedX, diffY = world.y - fixedY;
      const newWidth = Math.max(0.1, Math.abs(diffX * cosR + diffY * sinR));
      const newHeight = Math.max(0.1, Math.abs(diffX * (-sinR) + diffY * cosR));
      const newCx = (fixedX + world.x) / 2;
      const newCy = (fixedY + world.y) / 2;
      floorStore.resizeFurniture(furnitureDrag.id, newCx, newCy, newWidth, newHeight, { skipHistory: true });
    } else if (furnitureDrag.type === "rotate") {
      const { cx, cy } = furnitureDrag;
      const dx = world.x - cx, dy = world.y - cy;
      const rotation = Math.atan2(dx, -dy) * (180 / Math.PI);
      floorStore.rotateFurniture(furnitureDrag.id, rotation, { skipHistory: true });
    }
  }

  function endFurnitureDrag(): void {
    furnitureDrag = null;
  }

  const MIN_OPENING_WIDTH = 0.1;

  function handleOpeningHandleDragStart(openingId: string, side: "start" | "end"): void {
    floorStore.saveSnapshot(); toolStore.startOpeningDrag(openingId, side);
  }

  function handleOpeningHandleDrag(worldCursor: Point): void {
    const drag = toolStore.state.draggingOpeningHandle;
    if (!drag) return;
    const opening = floorStore.floor.openings.find((o) => o.id === drag.openingId);
    if (!opening) return;
    const wall = floorStore.floor.walls.find((w) => w.id === opening.wallId);
    if (!wall) return;
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const len = Math.hypot(dx, dy);
    if (len < 1e-9) return;
    const dirX = dx / len, dirY = dy / len;
    const cx = worldCursor.x - wall.start.x, cy = worldCursor.y - wall.start.y;
    const raw = Math.max(0, Math.min(len, cx * dirX + cy * dirY));
    const snapped = Math.max(0, Math.min(len, Math.round(raw / 0.1) * 0.1));
    if (drag.side === "end") {
      const newWidth = snapped - opening.offset;
      if (newWidth < MIN_OPENING_WIDTH) return;
      if (floorStore.openingOverlaps(wall.id, opening.id, opening.offset, snapped)) return;
      floorStore.updateOpening(opening.id, { width: newWidth }, { skipHistory: true });
    } else {
      const currentEnd = opening.offset + opening.width;
      const newOffset = snapped, newWidth = currentEnd - newOffset;
      if (newWidth < MIN_OPENING_WIDTH) return;
      if (floorStore.openingOverlaps(wall.id, opening.id, newOffset, currentEnd)) return;
      floorStore.updateOpening(opening.id, { offset: newOffset, width: newWidth }, { skipHistory: true });
    }
  }

  function handlePan(dx: number, dy: number): void { viewportStore.pan(dx, dy); }
  function handleZoom(screen: Point, factor: number): void { viewportStore.zoomAt(screen, factor); }

  function handleKeydown(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      commandPaletteOpen = true;
      return;
    }
    if (event.ctrlKey && event.key === "s") { event.preventDefault(); if (isFloorPlan && !viewMode) handleSave(); return; }
    const target = event.target as HTMLElement;
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;
    if (event.code === "Space") { event.preventDefault(); spacePressed = true; return; }
    if (viewMode) return;
    if (event.ctrlKey && event.key === "z" && !event.shiftKey) { event.preventDefault(); handleUndo(); return; }
    if (event.ctrlKey && (event.key === "y" || (event.key === "z" && event.shiftKey))) { event.preventDefault(); handleRedo(); return; }
    if (event.key === "Escape") {
      toolStore.resetDraw(); return;
    }
    if ((event.key === "Delete" || event.key === "Backspace") &&
        (toolStore.state.selectedId || toolStore.state.selectedOpeningId || selectedFurnitureId)) handleDelete();
  }

  function handleKeyup(event: KeyboardEvent): void {
    if (event.code === "Space") spacePressed = false;
  }

  function pointInPolygon(p: { x: number; y: number }, polygon: Array<{ x: number; y: number }>): boolean {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i].x, yi = polygon[i].y;
      const xj = polygon[j].x, yj = polygon[j].y;
      if ((yi > p.y) !== (yj > p.y) && p.x < (xj - xi) * (p.y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  function handleItemPointerDown(layerId: string, item: { id: string; name: string; emoji: string }, e: PointerEvent): void {
    draggingLayerId = layerId;
    draggingItemId = item.id;
    dragGhost = { x: e.clientX, y: e.clientY, emoji: item.emoji, label: item.name };
  }

  function handleFurniturePointerDown(templateId: string, e: PointerEvent): void {
    pointerDragFurnitureTemplateId = templateId;
    furniturePointerDownAt = { x: e.clientX, y: e.clientY };
    dragGhost = { x: e.clientX, y: e.clientY, emoji: "🪑", label: $_(`floorPlan.furnitureLibrary.items.${templateId}`) };
  }

  function cancelItemDrag(): void {
    draggingItemId = null;
    draggingLayerId = null;
    pointerDragFurnitureTemplateId = null;
    furniturePointerDownAt = null;
    dragGhost = null;
  }

  // A furniture item tapped/clicked rather than dragged releases at
  // (near) the same point it was picked up at -- which is still over the
  // picker panel, not the canvas. Treat that as "add at viewport center"
  // instead of dropping the object invisibly behind the panel.
  const FURNITURE_CLICK_THRESHOLD_PX = 6;

  function placeDraggedAt(clientX: number, clientY: number): void {
    if (viewMode) return;
    const canvasEl = document.querySelector(".canvas-area") as HTMLElement | null;
    if (!canvasEl) return;
    const rect = canvasEl.getBoundingClientRect();
    if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) return;

    if (pointerDragFurnitureTemplateId) {
      const template = getTemplate(pointerDragFurnitureTemplateId);
      if (template) {
        const wasClick = furniturePointerDownAt
          ? Math.hypot(clientX - furniturePointerDownAt.x, clientY - furniturePointerDownAt.y) < FURNITURE_CLICK_THRESHOLD_PX
          : false;
        const dropScreenX = wasClick ? rect.left + rect.width / 2 : clientX;
        const dropScreenY = wasClick ? rect.top + rect.height / 2 : clientY;
        const worldX = (dropScreenX - rect.left - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
        const worldY = (dropScreenY - rect.top - viewportStore.viewport.panY) / viewportStore.viewport.zoom;
        floorStore.addFurniture(pointerDragFurnitureTemplateId, worldX, worldY, template.defaultWidth, template.defaultHeight);
      }
      furniturePointerDownAt = null;
      return;
    }

    const layerId = draggingLayerId;
    const itemId = draggingItemId;
    if (!layerId || !itemId) return;

    if (allFloorsMode) {
      if (layerId !== "chores") return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: null, position: null, nextDueDate: chore?.nextDueDate ?? "", label: null });
      return;
    }

    const screenX = clientX - rect.left, screenY = clientY - rect.top;
    const worldX = (screenX - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
    const worldY = (screenY - viewportStore.viewport.panY) / viewportStore.viewport.zoom;

    if (layerId === "inventory") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      inventoryStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        roomId: room?.id ?? null,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "consumables") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      consumableStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        roomId: room?.id ?? null,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "costs") {
      settingsStore.placeCostCategory(itemId, {
        floorId: floorStore.currentFloorId,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "works") {
      worksStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "chores") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      if (!room) return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: room.id, position: { x: worldX, y: worldY }, nextDueDate: chore?.nextDueDate ?? "", label: null });
    }
  }

  function handleCanvasPointerUp(e: PointerEvent): void {
    placeDraggedAt(e.clientX, e.clientY);
  }
</script>

<svelte:window
  onkeydown={handleKeydown}
  onkeyup={handleKeyup}
  onblur={() => { spacePressed = false; }}
  onpointermove={(e) => { if (dragGhost) dragGhost = { ...dragGhost, x: e.clientX, y: e.clientY }; }}
  onpointerup={() => { handleDragEnd(); endFurnitureDrag(); cancelItemDrag(); }}
/>

<CommandPalette
  open={commandPaletteOpen}
  index={globalSearchIndex}
  onclose={() => { commandPaletteOpen = false; }}
  onselect={handleSearchSelect}
/>

{#if authStore.checking}
  <div class="auth-loading">{$_('common.loading')}</div>
{:else if !authStore.user}
  <LoginPage onlogin={() => {}} login={authStore.login} />
{:else}

<div class="app">
  <header class="topbar">
    <button
      class="hamburger"
      onclick={() => { navExpanded = !navExpanded; }}
      title={navExpanded ? $_('app.topbar.closeMenu') : $_('app.topbar.openMenu')}
    >{navExpanded ? "✕" : "☰"}</button>

    <span class="app-title">My Home</span>

    <span class="spacer"></span>
    <HomesSwitcher topbar={true} />
    <button class="icon-btn search-btn" title={$_('app.topbar.searchShortcut')} onclick={() => { commandPaletteOpen = true; }}>🔍</button>
    <NotificationBell store={notificationStore} onnavigate={handleNotificationSelect} />
    <button
      class="icon-btn theme-toggle"
      title={theme === "light" ? $_('app.topbar.switchToDark') : $_('app.topbar.switchToLight')}
      onclick={handleToggleTheme}
    >{theme === "light" ? "🌙" : "☀️"}</button>
    <span class="topbar-sep"></span>

    <div class="user-menu-wrap">
      <button
        class="icon-btn user-chip"
        onclick={() => { userMenuOpen = !userMenuOpen; }}
        title={$_('app.topbar.userMenu')}
      >
        {authStore.user?.username.slice(0, 2).toUpperCase()}
      </button>
      {#if userMenuOpen}
        <div class="user-dropdown">
          <div class="user-dropdown-header">
            <span class="user-dropdown-name">{authStore.user?.username}</span>
            <span class="user-role-badge">{authStore.user?.role}</span>
          </div>
          <hr class="user-dropdown-sep" />
          <button class="user-dropdown-item" onclick={() => { showChangePassword = true; userMenuOpen = false; }}>
            {$_('app.topbar.changePassword')}
          </button>
          <button class="user-dropdown-item signout" onclick={handleSignOut}>
            {$_('app.topbar.signOut')}
          </button>
        </div>
      {/if}
    </div>

  </header>

  <div class="workspace">
    <NavMenu {currentRoute} expanded={navExpanded} onclose={() => { navExpanded = false; }} />

    <div class="content">
      {#if homesStore.loaded && homesStore.homes.length === 0}
        <div class="no-homes">
          <p>{$_('app.noHomes')}</p>
        </div>
        <NewHomeModal open={true} required={true} onclose={() => {}} />

      {:else if isFloorPlan}
        <div class="canvas-area" bind:clientWidth={canvasWidth} bind:clientHeight={canvasHeight} onpointerup={handleCanvasPointerUp}>
          {#if !floorStore.loaded}
            <div class="loading">{$_('common.loading')}</div>
          {:else if allFloorsMode}
            <div class="all-floor-canvas">
              <div class="all-floor-hint">
                <span class="all-floor-icon">🏠</span>
                <span class="all-floor-title">{$_('app.allFloor.title')}</span>
                <span class="all-floor-sub">{$_('app.allFloor.sub')}</span>
              </div>
              {#each choreStore.houseAssignments() as a (a.id)}
                {@const chore = choreStore.chores.find(c => c.id === a.choreId)}
                {#if chore}
                  <div class="house-badge">
                    <span>{chore.emoji}</span>
                    <span>{choreDisplayName(chore.name, chore.emoji)}</span>
                    <button
                      class="house-badge-remove"
                      onclick={() => choreStore.deleteAssignment(a.id)}
                      title={$_('app.allFloor.removeAssignment')}
                    >✕</button>
                  </div>
                {/if}
              {/each}
            </div>
          {:else}
            <Canvas
              floor={floorStore.floor}
              viewport={viewportStore.viewport}
              width={canvasWidth}
              height={canvasHeight}
              selectedId={toolStore.state.selectedId}
              selectedOpeningId={toolStore.state.selectedOpeningId}
              selectedRoomId={toolStore.state.selectedRoomId}
              {selectedFurnitureId}
              furnitureObjects={floorStore.currentFurniture}
              onselect={handleSelect}
              onselectopening={handleSelectOpening}
              onselectroom={handleSelectRoom}
              onselectfurniture={handleSelectFurniture}
              onmovefurniturestart={handleMoveFurnitureStart}
              onresizefurniturestart={handleResizeFurnitureStart}
              onrotatefurniturestart={handleRotateFurnitureStart}
              tool={toolStore.state.tool}
              drawPoints={toolStore.state.drawPoints}
              cursorWorld={toolStore.state.cursorWorld}
              draggingPoint={toolStore.state.draggingPoint}
              {spacePressed}
              onpointermove={handlePointerMove}
              onplacepoint={handlePlacePoint}
              ondblclick={() => toolStore.resetDraw()}
              ondragstart={handleDragStart}
              ondragend={handleDragEnd}
              ondragopeninghandlestart={handleOpeningHandleDragStart}
              onpan={handlePan}
              onzoom={handleZoom}
              haLayerActive={haLayerActive}
              haStates={haStateStore.states}
              readOnly={viewMode}
            />
            {#if selectedOpening}
              <div class="opening-panel-float" style={opDrag.pos ? `left:${opDrag.pos.x}px;top:${opDrag.pos.y}px;right:auto;transform:none` : ''}>
                <OpeningPanel
                  opening={selectedOpening}
                  areaIds={selectedOpeningAreaIds}
                  readOnly={viewMode}
                  onupdate={(patch) => floorStore.updateOpening(selectedOpening.id, patch)}
                  onstartdrag={opDrag.startDrag}
                  ondismiss={() => toolStore.selectOpening(null)}
                />
              </div>
            {/if}
            {#if selectedRoom}
              <div class="room-panel-float" style={rpDrag.pos ? `left:${rpDrag.pos.x}px;top:${rpDrag.pos.y}px;right:auto;transform:none` : ''}>
                <RoomPanel
                  room={selectedRoom}
                  {haAreas}
                  readOnly={viewMode}
                  onupdate={(patch) => floorStore.updateRoom(selectedRoom.id, patch)}
                  onstartdrag={rpDrag.startDrag}
                  ondismiss={() => toolStore.selectRoom(null)}
                />
              </div>
            {/if}
            {#if selectedFurnitureObject && selectedFurnitureTemplate && selectedFurnitureTemplate.params?.length}
              <div class="furniture-params-panel-float" style={fpanelDrag.pos ? `left:${fpanelDrag.pos.x}px;top:${fpanelDrag.pos.y}px;right:auto;transform:none` : ''}>
                <FurnitureParamsPanel
                  object={selectedFurnitureObject}
                  template={selectedFurnitureTemplate}
                  readOnly={viewMode}
                  onupdate={(patch) => floorStore.updateFurnitureParams(selectedFurnitureObject.id, patch)}
                  onstartdrag={fpanelDrag.startDrag}
                  ondismiss={() => { selectedFurnitureId = null; }}
                />
              </div>
            {/if}
            {#if choreLayerActive}
              <ChoreOverlay
                chores={choreStore.chores}
                assignments={currentFloorAssignments}
                viewport={viewportStore.viewport}
                choreMode={true}
                width={canvasWidth}
                height={canvasHeight}
                onclick={(id) => handleBadgeClick(id)}
                ondragend={handleBadgeDragEnd}
              />
            {/if}
            {#if selectedBadge}
              {@const badge = selectedBadge}
              {#if badge}
                {@const chore = choreStore.chores.find((c) => c.id === badge.assignment.choreId)}
                {#if chore}
                  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                  <div style="position:absolute;inset:0;z-index:50" onclick={() => { selectedBadge = null; }}>
                    <BadgePopup
                      {chore}
                      assignment={badge.assignment}
                      screenX={badge.screenX}
                      screenY={badge.screenY}
                      oncomplete={async () => { await choreStore.completeAssignment(badge.assignment.id); selectedBadge = null; }}
                      oncompleteall={async () => { await choreStore.completeChore(chore.id); selectedBadge = null; }}
                      onremove={async () => { await choreStore.deleteAssignment(badge.assignment.id); selectedBadge = null; }}
                      onlabelchange={(label) => choreStore.updateAssignmentLabel(badge.assignment.id, label)}
                      onclose={() => { selectedBadge = null; }}
                    />
                  </div>
                {/if}
              {/if}
            {/if}
            {#if inventoryLayerActive}
            <InventoryOverlay
              items={currentFloorInventoryItems}
              viewport={viewportStore.viewport}
              active={true}
              width={canvasWidth}
              height={canvasHeight}
              onclick={(itemId) => {
                const item = inventoryStore.items.find((i) => i.id === itemId);
                if (!item?.placement) return;
                const sp = viewportStore.worldToScreen(item.placement.position);
                selectedInventoryPin = { item, screenX: sp.x, screenY: sp.y };
              }}
              ondragend={(itemId, worldPos) => {
                const item = inventoryStore.items.find((i) => i.id === itemId);
                if (!item?.placement) return;
                inventoryStore.setPlacement(itemId, {
                  ...item.placement,
                  position: worldPos,
                });
              }}
            />
            {/if}
            {#if selectedInventoryPin}
              {@const pin = selectedInventoryPin}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <div
                style="position:absolute;inset:0;z-index:55"
                onclick={() => { selectedInventoryPin = null; }}
              >
                <InventoryPinPopup
                  item={pin.item}
                  categoryName={settingsStore.inventoryCategories.find((c) => c.id === pin.item.categoryId)?.name ?? null}
                  screenX={pin.screenX}
                  screenY={pin.screenY}
                  onedit={() => {
                    selectedInventoryItemId = pin.item.id;
                    selectedInventoryPin = null;
                    window.location.hash = "#/inventory";
                  }}
                  onremove={async () => {
                    await inventoryStore.setPlacement(pin.item.id, null);
                    selectedInventoryPin = null;
                  }}
                  onclose={() => { selectedInventoryPin = null; }}
                />
              </div>
            {/if}
            {#if costsLayerActive}
              <CostsOverlay
                categories={currentFloorCostCategories}
                viewport={viewportStore.viewport}
                active={true}
                width={canvasWidth}
                height={canvasHeight}
                onclick={(catId) => {
                  const cat = settingsStore.costCategories.find((c) => c.id === catId);
                  if (!cat?.placement) return;
                  const sp = viewportStore.worldToScreen(cat.placement.position);
                  selectedCostCategoryPin = { category: cat, screenX: sp.x, screenY: sp.y };
                }}
                ondragend={(catId, worldPos) => {
                  const cat = settingsStore.costCategories.find((c) => c.id === catId);
                  if (!cat?.placement) return;
                  settingsStore.placeCostCategory(catId, {
                    ...cat.placement,
                    position: worldPos,
                  });
                }}
              />
            {/if}
            {#if selectedCostCategoryPin}
              {@const pin = selectedCostCategoryPin}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <div style="position:absolute;inset:0;z-index:55" onclick={() => { selectedCostCategoryPin = null; }}>
                <CostsPinPopup
                  category={pin.category}
                  screenX={pin.screenX}
                  screenY={pin.screenY}
                  onopen={() => {
                    selectedCostCategoryPin = null;
                    window.location.hash = "#/costs";
                  }}
                  onremove={async () => {
                    await settingsStore.placeCostCategory(pin.category.id, null);
                    selectedCostCategoryPin = null;
                  }}
                  onclose={() => { selectedCostCategoryPin = null; }}
                />
              </div>
            {/if}
            {#if worksLayerActive}
              <WorksOverlay
                works={currentFloorWorks}
                {settingsStore}
                viewport={viewportStore.viewport}
                active={true}
                width={canvasWidth}
                height={canvasHeight}
                onclick={(workId) => {
                  const work = worksStore.works.find((w) => w.id === workId);
                  if (!work?.placement) return;
                  const sp = viewportStore.worldToScreen(work.placement.position);
                  selectedWorkPin = { work, screenX: sp.x, screenY: sp.y };
                }}
                ondragend={(workId, worldPos) => {
                  const work = worksStore.works.find((w) => w.id === workId);
                  if (!work?.placement) return;
                  worksStore.setPlacement(workId, { ...work.placement, position: worldPos });
                }}
              />
            {/if}
            {#if selectedWorkPin}
              {@const pin = selectedWorkPin}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <div style="position:absolute;inset:0;z-index:55" onclick={() => { selectedWorkPin = null; }}>
                <WorksPinPopup
                  work={pin.work}
                  {settingsStore}
                  {contactsStore}
                  screenX={pin.screenX}
                  screenY={pin.screenY}
                  onopen={() => {
                    selectedWorkPin = null;
                    window.location.hash = "#/works";
                  }}
                  onremove={async () => {
                    await worksStore.setPlacement(pin.work.id, null);
                    selectedWorkPin = null;
                  }}
                  onclose={() => { selectedWorkPin = null; }}
                />
              </div>
            {/if}
            {#if consumablesLayerActive}
              <ConsumableOverlay
                consumables={currentFloorConsumables}
                viewport={viewportStore.viewport}
                active={true}
                width={canvasWidth}
                height={canvasHeight}
                onclick={(consumableId) => {
                  const c = consumableStore.consumables.find((x) => x.id === consumableId);
                  if (!c?.placement) return;
                  const sp = viewportStore.worldToScreen(c.placement.position);
                  selectedConsumablePin = { consumable: c, screenX: sp.x, screenY: sp.y };
                }}
                ondragend={(consumableId, worldPos) => {
                  const c = consumableStore.consumables.find((x) => x.id === consumableId);
                  if (!c?.placement) return;
                  consumableStore.setPlacement(consumableId, { ...c.placement, position: worldPos });
                }}
              />
            {/if}
            {#if selectedConsumablePin}
              {@const pin = selectedConsumablePin}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <div style="position:absolute;inset:0;z-index:55" onclick={() => { selectedConsumablePin = null; }}>
                <ConsumablePinPopup
                  consumable={pin.consumable}
                  store={consumableStore}
                  screenX={pin.screenX}
                  screenY={pin.screenY}
                  onedit={() => {
                    selectedConsumablePin = null;
                    window.location.hash = "#/consumables";
                  }}
                  onremove={async () => {
                    await consumableStore.setPlacement(pin.consumable.id, null);
                    selectedConsumablePin = null;
                  }}
                  onclose={() => { selectedConsumablePin = null; }}
                />
              </div>
            {/if}
          {/if}
          {#if pickerOpen && pickerLayers.length > 0}
            <div class="picker-float" style={ipDrag.pos ? `left:${ipDrag.pos.x}px;top:${ipDrag.pos.y}px;right:auto;transform:none` : ''}>
              <ItemPickerPanel
                layers={pickerLayers}
                draggingId={draggingItemId}
                highlightId={pickerHighlightId}
                onstartdrag={ipDrag.startDrag}
                ondismiss={() => { pickerOpen = false; }}
                onitempointerdown={(layerId, item, e) => { pickerHighlightId = null; handleItemPointerDown(layerId, item, e); }}
              />
            </div>
          {/if}
          {#if furnitureLibraryOpen}
            <div class="furniture-float" style={fpDrag.pos ? `left:${fpDrag.pos.x}px;top:${fpDrag.pos.y}px;right:auto;transform:none` : ''}>
              <FurnitureLibraryPanel onstartdrag={fpDrag.startDrag} ondismiss={() => { furnitureLibraryOpen = false; }} onitempointerdown={handleFurniturePointerDown} />
            </div>
          {/if}
          {#if floorStore.loaded}
            <!-- The FloorSwitcher below is the only way to leave whole-house
                 mode -- this block must stay visible while allFloorsMode is on. -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
              class="floating-toolbar"
              style={ftDrag.pos ? `left:${ftDrag.pos.x}px;top:${ftDrag.pos.y}px;right:auto;transform:none` : ''}
            >
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div class="ft-handle" onpointerdown={ftDrag.startDrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
              <div class="ft-sep"></div>
              <FloorSwitcher
                floors={floorStore.floors}
                currentFloorId={floorStore.currentFloorId}
                onswitchfloor={(id) => {
                  if (id === ALL_FLOOR_ID) { allFloorsMode = true; return; }
                  allFloorsMode = false;
                  floorStore.switchFloor(id);
                  toolStore.select(null);
                  toolStore.selectRoom(null);
                  toolStore.selectOpening(null);
                }}
                onaddfloor={viewMode ? undefined : (name) => {
                  allFloorsMode = false;
                  floorStore.addFloor(name);
                  toolStore.select(null);
                  toolStore.selectRoom(null);
                  toolStore.selectOpening(null);
                }}
                onrenamefloor={viewMode ? undefined : (id, name) => floorStore.renameFloor(id, name)}
                onremovefloor={viewMode ? undefined : (id) => floorStore.removeFloor(id)}
                compact={true}
              />
              <div class="ft-sep"></div>
              <LayersDropdown {activeLayers} ontoggle={toggleLayer} popoverAlign="left" variant="toolbar" />
              {#if !viewMode}
                <button
                  class="ft-btn"
                  class:active={pickerOpen}
                  title={$_('app.floatingToolbar.togglePicker')}
                  onclick={() => { pickerOpen = !pickerOpen; }}
                >📋 <span class="ft-label">{$_('app.floatingToolbar.picker')}</span></button>
                <button
                  class="ft-btn"
                  class:active={furnitureLibraryOpen}
                  title={$_('app.floatingToolbar.toggleFurniture')}
                  onclick={() => { furnitureLibraryOpen = !furnitureLibraryOpen; }}
                >🪑 <span class="ft-label">{$_('app.floatingToolbar.furniture')}</span></button>
              {/if}
              <div class="ft-sep"></div>
              <button
                class="ft-btn"
                class:active={viewMode}
                title={viewMode ? $_('app.floatingToolbar.switchToEditMode') : $_('app.floatingToolbar.switchToViewMode')}
                onclick={toggleViewMode}
              ><span class="mode-icon" class:crossed={viewMode}>✏️</span> <span class="ft-label">{viewMode ? $_('app.floatingToolbar.viewMode') : $_('app.floatingToolbar.editMode')}</span></button>
              {#if !viewMode}
                <button
                  class="ft-btn save-btn"
                  class:saved={saveStatus === "saved"}
                  class:save-error={saveStatus === "error"}
                  class:dirty={floorStore.isDirty && saveStatus === "idle"}
                  disabled={saveStatus === "saving"}
                  title={saveTitle}
                  onclick={handleSave}
                >{saveIcon} <span class="ft-label">{saveStatus === 'error' ? $_('app.floatingToolbar.errorLabel') : saveStatus === 'saving' ? $_('settings.security.saving') : saveStatus === 'saved' ? $_('app.floatingToolbar.saved') : $_('common.save')}</span></button>
              {/if}
              <button class="ft-btn ft-desktop-item" title={$_('app.floatingToolbar.resetView')} onclick={() => viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight)}>↺ <span class="ft-label">{$_('app.floatingToolbar.reset')}</span></button>
              {#if !viewMode}
                <div class="ft-sep ft-desktop-item"></div>
                <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.undo')} disabled={!floorStore.hasUndo} onclick={handleUndo}>↩ <span class="ft-label">{$_('app.floatingToolbar.undo')}</span></button>
                <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.redo')} disabled={!floorStore.hasRedo} onclick={handleRedo}>↪ <span class="ft-label">{$_('app.floatingToolbar.redo')}</span></button>
              {/if}
              {#if !choreLayerActive && !allFloorsMode}
                <div class="ft-sep ft-desktop-item"></div>
                <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.pan')} class:active={toolStore.state.tool === "pan"} onclick={() => toolStore.setTool("pan")}>✋ <span class="ft-label">{$_('floorPlan.tools.pan')}</span></button>
                {#if !viewMode}
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.select')} class:active={toolStore.state.tool === "select"} onclick={() => toolStore.setTool("select")}>🖱 <span class="ft-label">{$_('floorPlan.tools.select')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.wall')} class:active={toolStore.state.tool === "wall"} onclick={() => toolStore.setTool("wall")}>🧱 <span class="ft-label">{$_('floorPlan.tools.wall')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.divider')} class:active={toolStore.state.tool === "divider"} onclick={() => toolStore.setTool("divider")}>╌ <span class="ft-label">{$_('floorPlan.tools.divider')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.garden')} class:active={toolStore.state.tool === "garden"} onclick={() => toolStore.setTool("garden")}>🌿 <span class="ft-label">{$_('floorPlan.tools.garden')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.door')} class:active={toolStore.state.tool === "door"} onclick={() => toolStore.setTool("door")}>🚪 <span class="ft-label">{$_('floorPlan.tools.door')}</span></button>
                  <button class="ft-btn ft-desktop-item" title={$_('floorPlan.tools.window')} class:active={toolStore.state.tool === "window"} onclick={() => toolStore.setTool("window")}>🪟 <span class="ft-label">{$_('floorPlan.tools.window')}</span></button>
                  <div class="ft-sep ft-desktop-item"></div>
                  <button class="ft-btn ft-desktop-item delete" disabled={!hasSelection} onclick={handleDelete} title={$_('floorPlan.tools.delete')}>🗑 <span class="ft-label">{$_('app.floatingToolbar.delete')}</span></button>
                {/if}
              {/if}
              <div class="ft-sep ft-mobile-item"></div>
              <button class="ft-btn ft-mobile-item" bind:this={viewTriggerEl} title={$_('app.floatingToolbar.viewGroup')} onclick={() => { openGroup = "view"; }}>👁 <span class="ft-label">{$_('app.floatingToolbar.viewGroup')}</span></button>
              {#if !choreLayerActive && !allFloorsMode && !viewMode}
                <button class="ft-btn ft-mobile-item" bind:this={drawTriggerEl} title={$_('app.floatingToolbar.drawGroup')} onclick={() => { openGroup = "draw"; }}>📐 <span class="ft-label">{$_('app.floatingToolbar.drawGroup')}</span></button>
              {/if}
              {#if !viewMode}
                <button class="ft-btn ft-mobile-item" bind:this={actionsTriggerEl} title={$_('app.floatingToolbar.actionsGroup')} onclick={() => { openGroup = "actions"; }}>⚡ <span class="ft-label">{$_('app.floatingToolbar.actionsGroup')}</span></button>
              {/if}
            </div>
            <Popover open={openGroup === "view"} anchorEl={viewTriggerEl} onclose={() => { openGroup = null; }}>
              {#if !choreLayerActive && !allFloorsMode}
                <button class="ft-popover-row" class:active={toolStore.state.tool === "pan"} onclick={() => { toolStore.setTool("pan"); openGroup = null; }}><span class="ft-popover-icon">✋</span><span>{$_('floorPlan.tools.pan')}</span></button>
                {#if !viewMode}
                  <button class="ft-popover-row" class:active={toolStore.state.tool === "select"} onclick={() => { toolStore.setTool("select"); openGroup = null; }}><span class="ft-popover-icon">🖱</span><span>{$_('floorPlan.tools.select')}</span></button>
                {/if}
              {/if}
              <button class="ft-popover-row" onclick={() => { viewportStore.reset(floorStore.floor, canvasWidth, canvasHeight); openGroup = null; }}><span class="ft-popover-icon">↺</span><span>{$_('app.floatingToolbar.reset')}</span></button>
            </Popover>
            <Popover open={openGroup === "draw"} anchorEl={drawTriggerEl} onclose={() => { openGroup = null; }}>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "wall"} onclick={() => { toolStore.setTool("wall"); openGroup = null; }}><span class="ft-popover-icon">🧱</span><span>{$_('floorPlan.tools.wall')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "divider"} onclick={() => { toolStore.setTool("divider"); openGroup = null; }}><span class="ft-popover-icon">╌</span><span>{$_('floorPlan.tools.divider')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "garden"} onclick={() => { toolStore.setTool("garden"); openGroup = null; }}><span class="ft-popover-icon">🌿</span><span>{$_('floorPlan.tools.garden')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "door"} onclick={() => { toolStore.setTool("door"); openGroup = null; }}><span class="ft-popover-icon">🚪</span><span>{$_('floorPlan.tools.door')}</span></button>
              <button class="ft-popover-row" class:active={toolStore.state.tool === "window"} onclick={() => { toolStore.setTool("window"); openGroup = null; }}><span class="ft-popover-icon">🪟</span><span>{$_('floorPlan.tools.window')}</span></button>
            </Popover>
            <Popover open={openGroup === "actions"} anchorEl={actionsTriggerEl} onclose={() => { openGroup = null; }}>
              <button class="ft-popover-row" disabled={!floorStore.hasUndo} onclick={() => { handleUndo(); openGroup = null; }}><span class="ft-popover-icon">↩</span><span>{$_('app.floatingToolbar.undo')}</span></button>
              <button class="ft-popover-row" disabled={!floorStore.hasRedo} onclick={() => { handleRedo(); openGroup = null; }}><span class="ft-popover-icon">↪</span><span>{$_('app.floatingToolbar.redo')}</span></button>
              {#if !choreLayerActive && !allFloorsMode}
                <button class="ft-popover-row ft-popover-danger" disabled={!hasSelection} onclick={() => { handleDelete(); openGroup = null; }}><span class="ft-popover-icon">🗑</span><span>{$_('app.floatingToolbar.delete')}</span></button>
              {/if}
            </Popover>
            {#if !viewMode && !choreLayerActive && !allFloorsMode}
              <button
                class="ft-tool-indicator"
                title={$_(`floorPlan.tools.${toolStore.state.tool}`)}
                onclick={(e) => { e.stopPropagation(); openGroup = (toolStore.state.tool === "pan" || toolStore.state.tool === "select") ? "view" : "draw"; }}
              >{TOOL_ICONS[toolStore.state.tool]}</button>
            {/if}
          {/if}
        </div>

      {:else if isHome}
        <HomePage
          {floorStore}
          {choreStore}
          {inventoryStore}
          {settingsStore}
          {costsStore}
          {worksStore}
          {consumableStore}
          {locationsStore}
          {propertiesStore}
          {buildStore}
        />

      {:else if currentRoute === "#/chores" || currentRoute === "#/chores/manage"}
        <ChoresPage store={choreStore} {floorStore} selectedItemId={selectedChoreId} onclearselection={() => { selectedChoreId = null; }} onnewchore={() => { showNewChoreModal = true; }} onplaceonmap={(choreId) => { const next = new Set(activeLayers); next.add("chores"); activeLayers = next; pickerHighlightId = choreId; pickerOpen = true; window.location.hash = "#/plan"; }} />

      {:else if currentRoute === "#/inventory"}
        <InventoryPage
          store={inventoryStore}
          {floorStore}
          inventoryCategories={settingsStore.inventoryCategories}
          owners={settingsStore.owners}
          stores={settingsStore.stores}
          oncreatecategory={settingsStore.createInventoryCategory}
          oncreateowner={settingsStore.createOwner}
          oncreatestore={settingsStore.createStore}
          selectedItemId={selectedInventoryItemId}
          onclearselection={() => { selectedInventoryItemId = null; }}
          onplaceonmap={(id) => {
            const next = new Set(activeLayers);
            next.add("inventory");
            activeLayers = next;
            pickerHighlightId = id;
            pickerOpen = true;
            window.location.hash = "#/plan";
          }}
        />

      {:else if currentRoute === "#/consumables"}
        <ConsumablesPage
          store={consumableStore}
          {settingsStore}
          selectedItemId={selectedConsumableId}
          onclearselection={() => { selectedConsumableId = null; }}
          onplaceonmap={(id) => {
            const next = new Set(activeLayers);
            next.add("consumables");
            activeLayers = next;
            pickerHighlightId = id;
            pickerOpen = true;
            window.location.hash = "#/plan";
          }}
        />

      {:else if currentRoute === "#/works"}
        <WorksPage
          store={worksStore}
          {settingsStore}
          {contactsStore}
          selectedItemId={selectedWorkId}
          onclearselection={() => { selectedWorkId = null; }}
          onplaceonmap={(workId) => {
            const next = new Set(activeLayers);
            next.add("works");
            activeLayers = next;
            pickerHighlightId = workId;
            pickerOpen = true;
            window.location.hash = "#/plan";
          }}
        />

      {:else if currentRoute === "#/kb" || currentRoute.startsWith("#/kb/")}
        <KBPage store={kbStore} selectedItemId={kbRouteId} onnavigate={(id) => { window.location.hash = "#/kb/" + encodeURIComponent(id); }} />

      {:else if currentRoute === "#/costs"}
        <CostsPage
          {costsStore}
          {settingsStore}
          {contactsStore}
          {floorStore}
          selectedItemId={selectedCostEntryId}
          onclearselection={() => { selectedCostEntryId = null; }}
          onplaceonmap={(catId) => {
            const next = new Set(activeLayers);
            next.add("costs");
            activeLayers = next;
            pickerHighlightId = catId;
            pickerOpen = true;
            window.location.hash = "#/plan";
          }}
        />

      {:else if currentRoute === "#/settings"}
        <SettingsPage store={settingsStore} {authStore} importFromDonetick={choreStore.importFromDonetick} {reloadAllStores} />

      {:else if currentRoute === "#/locations"}
        <LocationsPage store={locationsStore} />
      {:else if currentRoute === "#/properties"}
        <PropertiesPage store={propertiesStore} {locationsStore} />
      {:else if currentRoute === "#/build"}
        <BuildPage store={buildStore} onopentask={(taskId) => { openBuildTaskId = taskId; }} />
      {:else if currentRoute === "#/contacts"}
        <ContactsPage store={contactsStore} {settingsStore} />
      {:else if currentRoute === "#/insurance"}
        <InsurancePage store={insuranceStore} {settingsStore} {contactsStore} />
      {/if}
    </div>
  </div>
</div>

{#if dragGhost}
  <div class="drag-ghost" style="left:{dragGhost.x + 12}px; top:{dragGhost.y + 12}px;">
    {dragGhost.emoji} {dragGhost.label}
  </div>
{/if}

<NewChoreModal open={showNewChoreModal} store={choreStore} onclose={() => { showNewChoreModal = false; }} />

{#if openBuildTaskId}
  <TaskModal
    task={buildStore.tasks.find((t) => t.id === openBuildTaskId) ?? null}
    store={buildStore}
    {contactsStore}
    onclose={() => { openBuildTaskId = null; }}
  />
{/if}

  {#if showChangePassword}
    <Modal title={$_('app.changePassword.title')} onclose={() => { showChangePassword = false; cpError = null; }}>
      <div style="display:flex;flex-direction:column;gap:12px;padding:4px 0">
        <Input label={$_('app.changePassword.currentPassword')} type="password" bind:value={cpCurrent} />
        <Input label={$_('app.changePassword.newPassword')} type="password" bind:value={cpNew} />
        {#if cpError}<div style="color:var(--danger);font-size:0.85rem">{cpError}</div>{/if}
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px">
          <Button variant="secondary" onclick={() => { showChangePassword = false; cpError = null; }}>{$_('common.cancel')}</Button>
          <Button onclick={handleChangePassword} disabled={cpLoading}>
            {cpLoading ? $_('app.changePassword.saving') : $_('app.changePassword.submit')}
          </Button>
        </div>
      </div>
    </Modal>
  {/if}

{/if}

<style>
  :global(body) { margin: 0; padding: 0; overflow: hidden; }

  .drag-ghost {
    position: fixed; pointer-events: none; z-index: 999;
    background: var(--surface); border: 1px solid var(--accent);
    border-radius: var(--radius-sm); padding: 4px 8px; font-size: 12px;
    box-shadow: var(--shadow-md); white-space: nowrap;
  }

  .app {
    display: flex; flex-direction: column;
    height: 100vh; font-family: var(--font-sans);
    background: var(--bg);
  }

  .topbar {
    height: 48px;
    background: var(--surface); color: var(--text);
    display: flex; align-items: center;
    padding: 0 var(--space-3); gap: var(--space-2);
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
  }

  .hamburger {
    width: 32px; height: 32px; flex-shrink: 0;
    border: none; background: transparent; color: var(--text-muted);
    font-size: 16px; cursor: pointer; border-radius: var(--radius-sm);
    display: flex; align-items: center; justify-content: center;
  }
  .hamburger:hover { background: var(--surface-hover); color: var(--text); }

  .app-title {
    font-size: 14px; font-weight: 600; color: var(--text);
    margin-right: var(--space-2); flex-shrink: 0;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .app-title { display: none; }
  }

  .theme-toggle { margin-right: var(--space-2); }

  .topbar-sep {
    width: 1px; height: 18px; background: var(--border); flex-shrink: 0; margin: 0 4px;
  }
  .spacer { flex: 1; }

  .toolbar {
    display: flex; align-items: center; gap: 2px; flex-shrink: 0;
  }
  .toolbar .sep {
    width: 1px; height: 16px; background: var(--border); margin: 0 3px; flex-shrink: 0;
  }
  .toolbar button {
    width: 28px; height: 28px;
    border: none; border-radius: var(--radius-sm); background: transparent;
    color: var(--text-muted); cursor: pointer; font-size: 14px;
    display: flex; align-items: center; justify-content: center; padding: 0;
  }
  .toolbar button:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  .toolbar button.active { background: var(--surface-hover); color: var(--accent); }
  .toolbar button.delete { color: var(--danger); }
  .toolbar button.delete:hover:not(:disabled) { background: var(--surface-hover); color: var(--danger); }
  .toolbar button:disabled { opacity: 0.35; cursor: default; }

  .icon-btn {
    width: 30px; height: 30px;
    border: none; border-radius: var(--radius-sm); background: transparent;
    color: var(--text-muted); cursor: pointer; font-size: 15px;
    display: flex; align-items: center; justify-content: center; padding: 0;
    flex-shrink: 0; text-decoration: none;
  }
  .icon-btn:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  .icon-btn.active { background: var(--surface-hover); color: var(--accent); }
  .icon-btn.save-btn { color: var(--success); position: relative; }
  .icon-btn.save-btn.dirty::after {
    content: '';
    position: absolute;
    top: 4px;
    right: 4px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    pointer-events: none;
  }
  .icon-btn.save-btn:hover:not(:disabled) { background: var(--surface-hover); }
  .icon-btn.save-btn.saved { color: var(--success); }
  .icon-btn.save-btn.save-error { color: var(--danger); }
  .icon-btn:disabled { opacity: 0.5; cursor: default; }

  .workspace {
    display: flex; flex: 1; overflow: hidden;
  }

  .content {
    display: flex; flex-direction: column;
    flex: 1; overflow: hidden; position: relative;
  }

  .canvas-area {
    flex: 1; overflow: hidden; position: relative;
  }

  .picker-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    max-height: min(460px, calc(100% - 16px));
    display: flex; flex-direction: column;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md); z-index: 20;
    overflow: hidden;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .picker-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
      z-index: 26;
    }
  }

  .furniture-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    max-height: min(460px, calc(100% - 16px));
    display: flex; flex-direction: column;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 0;
    box-shadow: var(--shadow-md); z-index: 20;
    overflow: hidden;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .furniture-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
      z-index: 26;
    }
  }

  .room-panel-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    z-index: 21;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .room-panel-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      z-index: 26;
    }
  }

  .opening-panel-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    z-index: 21;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .opening-panel-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      z-index: 26;
    }
  }

  .furniture-params-panel-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    z-index: 21;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .furniture-params-panel-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      z-index: 26;
    }
  }

  .floating-toolbar {
    position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
    display: flex; flex-direction: column; align-items: stretch; gap: 1px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 6px;
    box-shadow: var(--shadow-md); z-index: 25;
    user-select: none;
  }

  .ft-handle {
    text-align: center; cursor: grab; padding: 1px 0;
    color: var(--text-muted); font-size: 14px; letter-spacing: 3px;
    opacity: 0.5; border-radius: var(--radius-sm);
  }
  .ft-handle:hover { opacity: 1; background: var(--surface-hover); }
  .ft-handle:active { cursor: grabbing; }

  .ft-btn {
    width: 100%; height: 28px;
    border: none; border-radius: var(--radius-sm); background: transparent;
    color: var(--text-muted); cursor: pointer; font-size: 13px;
    display: flex; align-items: center; gap: 5px; padding: 0 6px;
    flex-shrink: 0; white-space: nowrap;
  }
  .ft-btn:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  .ft-btn.active { background: var(--surface-hover); color: var(--accent); }
  .ft-btn.delete { color: var(--danger); }
  .ft-btn.delete:hover:not(:disabled) { background: var(--surface-hover); color: var(--danger); }
  .ft-btn:disabled { opacity: 0.35; cursor: default; }

  .ft-btn.save-btn { color: var(--success); position: relative; }
  .ft-btn.save-btn.dirty::after {
    content: ''; position: absolute; top: 4px; right: 4px;
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--accent); pointer-events: none;
  }
  .ft-btn.save-btn:hover:not(:disabled) { background: var(--surface-hover); }
  .ft-btn.save-btn.saved { color: var(--success); }
  .ft-btn.save-btn.save-error { color: var(--danger); }

  .ft-label { font-size: 11px; font-weight: 500; }

  .mode-icon {
    position: relative;
    display: inline-block;
    line-height: 1;
  }
  .mode-icon.crossed::after {
    content: '';
    position: absolute;
    left: -2px; right: -2px; top: 50%;
    height: 2px;
    background: var(--danger);
    transform: translateY(-50%) rotate(-45deg);
    border-radius: 1px;
  }

  .ft-sep {
    height: 1px; background: var(--border); flex-shrink: 0; margin: 2px 0;
  }

  .ft-mobile-item { display: none; }

  .ft-tool-indicator {
    display: none;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: 50%;
    background: var(--surface);
    box-shadow: var(--shadow-md);
    font-size: 18px;
    cursor: pointer;
  }

  .ft-popover-row {
    display: flex; align-items: center; gap: 10px; width: 100%;
    padding: 10px 12px; min-height: 44px;
    border: none; border-radius: var(--radius-sm);
    background: transparent; color: var(--text);
    font-size: 14px; cursor: pointer; text-align: left;
  }
  .ft-popover-row:hover:not(:disabled) { background: var(--surface-hover); }
  .ft-popover-row.active { background: var(--surface-hover); color: var(--accent); }
  .ft-popover-row:disabled { opacity: 0.35; cursor: default; }
  .ft-popover-row.ft-popover-danger { color: var(--danger); }
  .ft-popover-icon { font-size: 20px; width: 24px; text-align: center; flex-shrink: 0; }

  @media (max-width: 480px) { /* --bp-mobile */
    .floating-toolbar {
      position: fixed;
      left: 0; right: 0; bottom: 0; top: auto;
      transform: none !important;
      box-sizing: border-box;
      width: 100%;
      height: 48px;
      padding: 4px;
      flex-direction: row;
      align-items: center;
      gap: 0;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
      z-index: 30;
    }
    .ft-handle { display: none; }
    .ft-btn {
      flex: 1 1 0;
      max-width: 44px;
      width: auto;
      aspect-ratio: 1 / 1;
      justify-content: center;
      font-size: 22px;
    }
    .ft-label { display: none; }
    .ft-sep { width: 1px; height: 24px; margin: 0 2px; flex-shrink: 0; }
    .ft-desktop-item { display: none; }
    .ft-mobile-item { display: flex; }
    .ft-tool-indicator {
      display: flex; align-items: center; justify-content: center;
      position: fixed; right: 8px; bottom: 56px;
      width: 40px; height: 40px;
      z-index: 31;
    }
  }

  .loading {
    display: flex; align-items: center; justify-content: center;
    height: 100%; color: #888; font-size: 14px;
  }

  .all-floor-canvas {
    flex: 1; display: flex; flex-direction: column; align-items: center;
    padding: 40px 24px; gap: 12px; background: #111122; overflow-y: auto;
  }
  .all-floor-hint {
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    margin-bottom: 24px;
  }
  .all-floor-icon { font-size: 40px; }
  .all-floor-title { font-size: 18px; color: #eee; font-weight: 600; }
  .all-floor-sub { font-size: 12px; color: #667; }
  .house-badge {
    display: flex; align-items: center; gap: 10px; padding: 8px 16px;
    background: #1e1e2e; border: 1px solid #333; border-radius: 6px;
    color: #ccc; font-size: 13px; min-width: 200px;
  }
  .house-badge-remove {
    margin-left: auto; border: none; background: transparent; color: #666;
    cursor: pointer; font-size: 11px; padding: 2px 5px;
  }
  .house-badge-remove:hover { color: #f66; }

  .placeholder {
    display: flex; align-items: center; justify-content: center;
    height: 100%; color: #556; font-size: 14px;
  }

  .auth-loading {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  .user-menu-wrap { position: relative; margin-left: auto; }

  .user-chip {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .user-dropdown {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    min-width: 180px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 0;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    z-index: 200;
  }

  .user-dropdown-header {
    padding: 8px 14px 6px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .user-dropdown-name { font-size: 0.9rem; color: var(--text); font-weight: 600; }

  .user-role-badge {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .user-dropdown-sep { margin: 4px 0; border: none; border-top: 1px solid var(--border); }

  .user-dropdown-item {
    display: block;
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    padding: 8px 14px;
    font-size: 0.875rem;
    color: var(--text);
    cursor: pointer;
    font-family: var(--font-sans);
  }

  .user-dropdown-item:hover { background: var(--surface-hover, var(--border)); }
  .user-dropdown-item.signout { color: var(--danger, #e05); }

  .no-homes {
    display: flex; align-items: center; justify-content: center;
    height: 100%; color: var(--text-muted); font-size: 14px;
  }
</style>
