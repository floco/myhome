<script lang="ts">
  import type { Point, WallType } from "@myhome/geometry";
  import { pointsEqual } from "@myhome/geometry";
  import { createHouseStore } from "./lib/houseStore.svelte";
  import { createViewportStore } from "./lib/viewportStore.svelte";
  import { createToolStore } from "./lib/toolStore.svelte";
  import { placePoint, allEndpoints } from "./lib/drawingTool";
  import { findSnapPoint, snapToGrid, SNAP_RADIUS_PX, hitTestWall, HIT_RADIUS_PX } from "./lib/geometry-helpers";
  import type { Opening } from "@myhome/geometry";
  import Canvas from "./lib/components/Canvas.svelte";
  import RoomPanel from "./lib/components/RoomPanel.svelte";
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
  import { getStoredTheme, toggleTheme, type Theme } from "./lib/theme";
  import { createAuthStore } from "./lib/authStore.svelte";
  import LoginPage from "./lib/components/LoginPage.svelte";
  import Modal from "./lib/components/ui/Modal.svelte";
  import Input from "./lib/components/ui/Input.svelte";
  import Button from "./lib/components/ui/Button.svelte";
  import { homesStore } from "./lib/homesStore.svelte";
  import NewHomeModal from "./lib/components/NewHomeModal.svelte";
  import HomesSwitcher from "./lib/components/HomesSwitcher.svelte";
  import PlaceholderPage from "./lib/components/PlaceholderPage.svelte";

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
  const authStore = createAuthStore();

  homesStore.loadHomes();

  $effect(() => {
    const _homeId = homesStore.activeHomeId;
    floorStore.reload();
    choreStore.reload();
    inventoryStore.reload();
    settingsStore.reload();
    costsStore.reload();
    worksStore.reload();
    kbStore.reload();
    consumableStore.reload();
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

  let activeLayers = $state(new Set<string>());
  const choreLayerActive = $derived(activeLayers.has("chores"));
  const inventoryLayerActive = $derived(activeLayers.has("inventory"));
  const costsLayerActive = $derived(activeLayers.has("costs"));
  const currentFloorCostCategories = $derived(
    settingsStore.costCategories.filter(c => c.placement?.floorId === floorStore.currentFloorId)
  );
  const worksLayerActive = $derived(activeLayers.has("works"));
  const consumablesLayerActive = $derived(activeLayers.has("consumables"));
  const currentFloorConsumables = $derived(
    consumableStore.consumables.filter(c => c.placement?.floorId === floorStore.currentFloorId)
  );
  const consumablesPickerLayer = $derived<PickerLayer>({
    id: "consumables",
    label: "Consumables",
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
    label: "Works",
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
    label: "Chores",
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
    label: "Inventory",
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
    label: "Costs",
    emoji: "💶",
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
  let allFloorsMode = $state(false);
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
      cpError = e instanceof Error ? e.message : "Failed";
    } finally {
      cpLoading = false;
    }
  }

  async function handleSignOut(): Promise<void> {
    await authStore.logout();
    userMenuOpen = false;
  }

  let currentRoute = $state(window.location.hash || "#/");
  $effect(() => {
    const onHashChange = () => { currentRoute = window.location.hash || "#/"; };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  });

  const isFloorPlan = $derived(currentRoute === "#/plan");
  const isHome = $derived(currentRoute === "#/" || currentRoute === "");

  const selectedRoom = $derived(
    toolStore.state.selectedRoomId
      ? (floorStore.floor.rooms.find((r) => r.id === toolStore.state.selectedRoomId) ?? null)
      : null
  );

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
  let haAreas = $state<Array<{ area_id: string; name: string }>>([]);

  const hasSelection = $derived(
    toolStore.state.selectedId !== null || toolStore.state.selectedOpeningId !== null
  );
  const saveIcon = $derived(
    saveStatus === "saving" ? "⋯" : saveStatus === "saved" ? "✓" : saveStatus === "error" ? "⚠" : "💾"
  );
  const saveTitle = $derived(
    saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "Saved" : saveStatus === "error" ? "Save error!" : "Save"
  );

  async function handleSave(): Promise<void> {
    saveStatus = "saving";
    try {
      await floorStore.save();
      saveStatus = "saved";
      setTimeout(() => { saveStatus = "idle"; }, 2000);
    } catch {
      saveStatus = "error";
      setTimeout(() => { saveStatus = "idle"; }, 4000);
    }
  }

  $effect(() => {
    fetch("/api/ha/areas")
      .then((r) => r.json())
      .then((areas: Array<{ area_id: string; name: string }>) => { haAreas = areas; })
      .catch(() => { haAreas = []; });
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
    const { selectedId, selectedOpeningId } = toolStore.state;
    if (selectedId) { floorStore.removeWall(selectedId); toolStore.select(null); }
    else if (selectedOpeningId) { floorStore.removeOpening(selectedOpeningId); toolStore.selectOpening(null); }
  }

  function handleUndo(): void {
    floorStore.undo(); toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null);
  }

  function handleRedo(): void {
    floorStore.redo(); toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null);
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
    const target = event.target as HTMLElement;
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;
    if (event.code === "Space") { event.preventDefault(); spacePressed = true; return; }
    if (event.ctrlKey && event.key === "z" && !event.shiftKey) { event.preventDefault(); handleUndo(); return; }
    if (event.ctrlKey && (event.key === "y" || (event.key === "z" && event.shiftKey))) { event.preventDefault(); handleRedo(); return; }
    if (event.key === "Escape") {
      toolStore.resetDraw(); return;
    }
    if ((event.key === "Delete" || event.key === "Backspace") &&
        (toolStore.state.selectedId || toolStore.state.selectedOpeningId)) handleDelete();
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

  function handleDragOver(e: DragEvent): void {
    if (!draggingItemId) return;
    e.preventDefault();
  }

  function handleDrop(e: DragEvent): void {
    e.preventDefault();
    const layerId = e.dataTransfer?.getData("pickerLayer") ?? draggingLayerId;
    const itemId = e.dataTransfer?.getData("pickerId") ?? draggingItemId;
    draggingItemId = null;
    draggingLayerId = null;
    if (!layerId || !itemId) return;

    if (allFloorsMode) {
      if (layerId !== "chores") return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: null, position: null, nextDueDate: chore?.nextDueDate ?? "" });
      return;
    }

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const screenX = e.clientX - rect.left, screenY = e.clientY - rect.top;
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
      choreStore.createAssignment({ choreId: itemId, roomId: room.id, position: { x: worldX, y: worldY }, nextDueDate: chore?.nextDueDate ?? "" });
    }
  }
</script>

<svelte:window
  onkeydown={handleKeydown}
  onkeyup={handleKeyup}
  onblur={() => { spacePressed = false; }}
  onmouseup={handleDragEnd}
/>

{#if authStore.checking}
  <div class="auth-loading">Loading…</div>
{:else if !authStore.user}
  <LoginPage onlogin={() => {}} login={authStore.login} />
{:else}

<div class="app">
  <header class="topbar">
    <button
      class="hamburger"
      onclick={() => { navExpanded = !navExpanded; }}
      title={navExpanded ? "Close menu" : "Open menu"}
    >{navExpanded ? "✕" : "☰"}</button>

    <span class="app-title">My Home</span>

    <button
      class="icon-btn theme-toggle"
      title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
      onclick={handleToggleTheme}
    >{theme === "light" ? "🌙" : "☀️"}</button>

    {#if isFloorPlan}
      <FloorSwitcher
        floors={floorStore.floors}
        currentFloorId={allFloorsMode ? ALL_FLOOR_ID : floorStore.currentFloorId}
        onswitchfloor={(id) => {
          if (id === ALL_FLOOR_ID) { allFloorsMode = true; return; }
          allFloorsMode = false;
          floorStore.switchFloor(id);
          toolStore.select(null);
          toolStore.selectRoom(null);
          toolStore.selectOpening(null);
        }}
        onaddfloor={(name) => floorStore.addFloor(name)}
        onrenamefloor={(id, name) => floorStore.renameFloor(id, name)}
        onremovefloor={(id) => floorStore.removeFloor(id)}
      />

      <span class="spacer"></span>

      {#if !choreLayerActive}
        <div class="toolbar">
          <button title="Undo (Ctrl+Z)" disabled={!floorStore.hasUndo} onclick={handleUndo}>↩</button>
          <button title="Redo (Ctrl+Y)" disabled={!floorStore.hasRedo} onclick={handleRedo}>↪</button>
          <span class="sep"></span>
          <button title="Select" class:active={toolStore.state.tool === "select"} onclick={() => toolStore.setTool("select")}>🖱</button>
          <button title="Wall" class:active={toolStore.state.tool === "wall"} onclick={() => toolStore.setTool("wall")}>🧱</button>
          <button title="Divider" class:active={toolStore.state.tool === "divider"} onclick={() => toolStore.setTool("divider")}>╌</button>
          <button title="Door" class:active={toolStore.state.tool === "door"} onclick={() => toolStore.setTool("door")}>🚪</button>
          <button title="Window" class:active={toolStore.state.tool === "window"} onclick={() => toolStore.setTool("window")}>🪟</button>
          <span class="sep"></span>
          <button title="Delete selected (Del)" class="delete" disabled={!hasSelection} onclick={handleDelete}>🗑</button>
        </div>
      {/if}

      <span class="topbar-sep"></span>

      <LayersDropdown {activeLayers} ontoggle={toggleLayer} />
      <button
        class="icon-btn"
        class:active={pickerOpen}
        title="Toggle item picker"
        onclick={() => { pickerOpen = !pickerOpen; }}
      >📋</button>
      <button
        class="icon-btn save-btn"
        class:saved={saveStatus === "saved"}
        class:save-error={saveStatus === "error"}
        disabled={saveStatus === "saving"}
        title={saveTitle}
        onclick={handleSave}
      >{saveIcon}</button>
      <button class="icon-btn" title="Reset view" onclick={() => viewportStore.reset()}>↺</button>
      <span class="topbar-sep"></span>
    {/if}

    <div class="user-menu-wrap">
      <button
        class="icon-btn user-chip"
        onclick={() => { userMenuOpen = !userMenuOpen; }}
        title="User menu"
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
            Change password
          </button>
          <button class="user-dropdown-item signout" onclick={handleSignOut}>
            Sign out
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
          <p>Create your first home to get started.</p>
        </div>
        <NewHomeModal open={true} required={true} onclose={() => {}} />

      {:else if isFloorPlan}
        <div class="canvas-area" bind:clientWidth={canvasWidth} bind:clientHeight={canvasHeight} ondragover={handleDragOver} ondrop={handleDrop}>
          {#if !floorStore.loaded}
            <div class="loading">Loading…</div>
          {:else if allFloorsMode}
            <div class="all-floor-canvas">
              <div class="all-floor-hint">
                <span class="all-floor-icon">🏠</span>
                <span class="all-floor-title">House-wide</span>
                <span class="all-floor-sub">Drag chores here to assign to the whole house</span>
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
                      title="Remove house-wide assignment"
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
              onselect={handleSelect}
              onselectopening={handleSelectOpening}
              onselectroom={handleSelectRoom}
              tool={toolStore.state.tool}
              drawPoints={toolStore.state.drawPoints}
              cursorWorld={toolStore.state.cursorWorld}
              {spacePressed}
              onpointermove={handlePointerMove}
              onplacepoint={handlePlacePoint}
              ondblclick={() => toolStore.resetDraw()}
              ondragstart={handleDragStart}
              ondragend={handleDragEnd}
              ondragopeninghandlestart={handleOpeningHandleDragStart}
              onpan={handlePan}
              onzoom={handleZoom}
            />
            {#if selectedRoom}
              <RoomPanel
                room={selectedRoom}
                {haAreas}
                onupdate={(patch) => floorStore.updateRoom(selectedRoom.id, patch)}
              />
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
            <div class="right-panels">
              <ItemPickerPanel
                layers={pickerLayers}
                draggingId={draggingItemId}
                highlightId={pickerHighlightId}
                ondragstart={(layerId, itemId, _e) => { draggingLayerId = layerId; draggingItemId = itemId; pickerHighlightId = null; }}
                ondragend={() => { draggingLayerId = null; draggingItemId = null; }}
              />
            </div>
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
        />

      {:else if currentRoute === "#/chores" || currentRoute === "#/chores/manage"}
        <ChoresPage store={choreStore} {floorStore} onnewchore={() => { showNewChoreModal = true; }} onplaceonmap={(choreId) => { const next = new Set(activeLayers); next.add("chores"); activeLayers = next; pickerHighlightId = choreId; pickerOpen = true; window.location.hash = "#/plan"; }} />

      {:else if currentRoute === "#/inventory"}
        <InventoryPage
          store={inventoryStore}
          {floorStore}
          inventoryCategories={settingsStore.inventoryCategories.map(c => c.name)}
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
          onplaceonmap={(workId) => {
            const next = new Set(activeLayers);
            next.add("works");
            activeLayers = next;
            pickerHighlightId = workId;
            pickerOpen = true;
            window.location.hash = "#/plan";
          }}
        />

      {:else if currentRoute === "#/kb"}
        <KBPage store={kbStore} />

      {:else if currentRoute === "#/costs"}
        <CostsPage
          {costsStore}
          {settingsStore}
          {floorStore}
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
        <SettingsPage store={settingsStore} {authStore} />

      {:else if currentRoute === "#/locations"}
        <PlaceholderPage icon="🌍" label="Locations" description="Pin and compare candidate locations on a map." />
      {:else if currentRoute === "#/properties"}
        <PlaceholderPage icon="🏘" label="Properties" description="Track property listings, prices, and details." />
      {:else if currentRoute === "#/budget"}
        <PlaceholderPage icon="💰" label="Budget" description="Plan and track your acquisition or build budget." />
      {:else if currentRoute === "#/visits"}
        <PlaceholderPage icon="📅" label="Visits" description="Schedule and log site visits and viewings." />
      {:else if currentRoute === "#/contacts"}
        <PlaceholderPage icon="👤" label="Contacts" description="Manage agents, notaries, builders, and other contacts." />
      {:else if currentRoute === "#/checklist"}
        <PlaceholderPage icon="✅" label="Checklist" description="Track tasks and due diligence items for your project." />
      {/if}
    </div>
  </div>
</div>

<NewChoreModal open={showNewChoreModal} store={choreStore} onclose={() => { showNewChoreModal = false; }} />

  {#if showChangePassword}
    <Modal title="Change Password" onclose={() => { showChangePassword = false; cpError = null; }}>
      <div style="display:flex;flex-direction:column;gap:12px;padding:4px 0">
        <Input label="Current password" type="password" bind:value={cpCurrent} />
        <Input label="New password (min 8 chars)" type="password" bind:value={cpNew} />
        {#if cpError}<div style="color:var(--danger);font-size:0.85rem">{cpError}</div>{/if}
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px">
          <Button variant="secondary" onclick={() => { showChangePassword = false; cpError = null; }}>Cancel</Button>
          <Button onclick={handleChangePassword} disabled={cpLoading}>
            {cpLoading ? "Saving…" : "Change password"}
          </Button>
        </div>
      </div>
    </Modal>
  {/if}

{/if}

<style>
  :global(body) { margin: 0; padding: 0; overflow: hidden; }

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
  .icon-btn.save-btn { color: var(--success); }
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

  .right-panels {
    position: absolute; top: 0; right: 0; bottom: 0;
    display: flex; flex-direction: row; z-index: 20;
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
