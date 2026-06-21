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
  import ChoreListPage from "./lib/components/ChoreListPage.svelte";
  import NavMenu from "./lib/components/NavMenu.svelte";
  import NewChoreModal from "./lib/components/NewChoreModal.svelte";
  import LayersDropdown from "./lib/components/LayersDropdown.svelte";
  import InventoryPage from "./lib/components/InventoryPage.svelte";
  import ConsumablesPage from "./lib/components/ConsumablesPage.svelte";
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

  const floorStore = createHouseStore();
  const viewportStore = createViewportStore();
  const toolStore = createToolStore();
  const choreStore = createChoreStore();
  const inventoryStore = createInventoryStore();
  const settingsStore = createSettingsStore();
  const costsStore = createCostsStore();

  let selectedInventoryPin = $state<{
    item: InventoryItem;
    screenX: number;
    screenY: number;
  } | null>(null);
  let selectedInventoryItemId = $state<string | null>(null);
  let draggingItemId = $state<string | null>(null);
  let draggingLayerId = $state<string | null>(null);

  let selectedCostCategoryPin = $state<{
    category: CostCategory;
    screenX: number;
    screenY: number;
  } | null>(null);
  let placingCostCategoryId = $state<string | null>(null);

  let activeLayers = $state(new Set<string>());
  const choreLayerActive = $derived(activeLayers.has("chores"));
  const inventoryLayerActive = $derived(activeLayers.has("inventory"));
  const costsLayerActive = $derived(activeLayers.has("costs"));
  const currentFloorCostCategories = $derived(
    settingsStore.costCategories.filter(c => c.placement?.floorId === floorStore.currentFloorId)
  );

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

  const pickerLayers = $derived<PickerLayer[]>([
    ...(choreLayerActive ? [chorePickerLayer] : []),
    ...(inventoryLayerActive ? [inventoryPickerLayer] : []),
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

  let currentRoute = $state(window.location.hash || "#/");
  $effect(() => {
    const onHashChange = () => { currentRoute = window.location.hash || "#/"; };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  });

  const isFloorPlan = $derived(currentRoute === "#/" || currentRoute === "");
  const isChores = $derived(currentRoute.startsWith("#/chores"));

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
    if (event.code === "Space") { event.preventDefault(); spacePressed = true; return; }
    if (event.ctrlKey && event.key === "z" && !event.shiftKey) { event.preventDefault(); handleUndo(); return; }
    if (event.ctrlKey && (event.key === "y" || (event.key === "z" && event.shiftKey))) { event.preventDefault(); handleRedo(); return; }
    if (event.key === "Escape") {
      if (placingCostCategoryId) { placingCostCategoryId = null; return; }
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

<div class="app">
  <header class="topbar">
    <button
      class="hamburger"
      onclick={() => { navExpanded = !navExpanded; }}
      title={navExpanded ? "Close menu" : "Open menu"}
    >{navExpanded ? "✕" : "☰"}</button>

    <span class="app-title">myhome</span>

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

    {#if isChores}
      {#if !isFloorPlan}<span class="spacer"></span>{/if}
      <a
        href={currentRoute === "#/chores/manage" ? "#/chores" : "#/chores/manage"}
        class="icon-btn"
        class:active={currentRoute === "#/chores/manage"}
        title="Chore settings"
      >⚙</a>
      <button
        class="icon-btn new-chore-btn"
        title="New chore"
        onclick={() => { showNewChoreModal = true; }}
      >＋</button>
    {/if}
  </header>

  <div class="workspace">
    <NavMenu {currentRoute} expanded={navExpanded} onclose={() => { navExpanded = false; }} />

    <div class="content">
      {#if isFloorPlan}
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
            {#if pickerOpen && pickerLayers.length > 0}
              <div class="right-panels">
                <ItemPickerPanel
                  layers={pickerLayers}
                  draggingId={draggingItemId}
                  ondragstart={(layerId, itemId, _e) => { draggingLayerId = layerId; draggingItemId = itemId; }}
                  ondragend={() => { draggingLayerId = null; draggingItemId = null; }}
                />
              </div>
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
            {#if placingCostCategoryId}
              {@const placingCat = settingsStore.costCategories.find(c => c.id === placingCostCategoryId)}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <div
                style="position:absolute;inset:0;z-index:70;cursor:crosshair"
                onclick={(e) => {
                  if (!placingCostCategoryId) return;
                  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                  const screenX = e.clientX - rect.left;
                  const screenY = e.clientY - rect.top;
                  const worldPos = viewportStore.screenToWorld({ x: screenX, y: screenY });
                  settingsStore.placeCostCategory(placingCostCategoryId, {
                    floorId: floorStore.currentFloorId,
                    position: worldPos,
                  });
                  placingCostCategoryId = null;
                }}
              >
                <div style="position:absolute;top:8px;left:50%;transform:translateX(-50%);background:#1e1e3a;border:1px solid #5566cc;border-radius:6px;padding:6px 14px;color:#aaf;font-size:12px;font-family:sans-serif;pointer-events:none">
                  {#if placingCat}
                    Click to place {placingCat.emoji} {placingCat.name}
                  {:else}
                    Click to place pin
                  {/if}
                  &nbsp;&nbsp;<span style="color:#556;font-size:10px">Press Esc to cancel</span>
                </div>
              </div>
            {/if}
          {/if}
        </div>

      {:else if currentRoute === "#/chores"}
        <ChoreListPage store={choreStore} {floorStore} />

      {:else if currentRoute === "#/chores/manage"}
        <ChoresPage store={choreStore} {floorStore} onnewchore={() => { showNewChoreModal = true; }} />

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
            window.location.hash = "#/";
          }}
        />

      {:else if currentRoute === "#/consumables"}
        <ConsumablesPage />

      {:else if currentRoute === "#/works"}
        <WorksPage />

      {:else if currentRoute === "#/costs"}
        <CostsPage
          {costsStore}
          {settingsStore}
          {floorStore}
          onplaceonmap={(catId) => {
            placingCostCategoryId = catId;
            const next = new Set(activeLayers);
            next.add("costs");
            activeLayers = next;
            window.location.hash = "#/";
          }}
        />

      {:else if currentRoute === "#/settings"}
        <SettingsPage store={settingsStore} />
      {/if}
    </div>
  </div>
</div>

<NewChoreModal open={showNewChoreModal} store={choreStore} onclose={() => { showNewChoreModal = false; }} />

<style>
  :global(body) { margin: 0; padding: 0; overflow: hidden; }

  .app {
    display: flex; flex-direction: column;
    height: 100vh; font-family: sans-serif;
    background: #1a1a2e;
  }

  .topbar {
    height: 36px;
    background: #1e1e2e; color: #ccc;
    display: flex; align-items: center;
    padding: 0 8px; gap: 8px;
    flex-shrink: 0;
    border-bottom: 1px solid #2a2a3a;
  }

  .hamburger {
    width: 32px; height: 32px; flex-shrink: 0;
    border: none; background: transparent; color: #999;
    font-size: 16px; cursor: pointer; border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
  }
  .hamburger:hover { background: #2a2a4a; color: #eee; }

  .app-title {
    font-size: 14px; font-weight: 600; color: #eee;
    margin-right: 8px; flex-shrink: 0;
  }

  .topbar-sep {
    width: 1px; height: 18px; background: #333; flex-shrink: 0; margin: 0 4px;
  }
  .spacer { flex: 1; }

  .toolbar {
    display: flex; align-items: center; gap: 2px; flex-shrink: 0;
  }
  .toolbar .sep {
    width: 1px; height: 16px; background: #333; margin: 0 3px; flex-shrink: 0;
  }
  .toolbar button {
    width: 28px; height: 28px;
    border: none; border-radius: 4px; background: transparent;
    color: #999; cursor: pointer; font-size: 14px;
    display: flex; align-items: center; justify-content: center; padding: 0;
  }
  .toolbar button:hover:not(:disabled) { background: #2a2a4a; color: #eee; }
  .toolbar button.active { background: #2a2a5a; color: #aaf; }
  .toolbar button.delete { color: #c66; }
  .toolbar button.delete:hover:not(:disabled) { background: #422; color: #f88; }
  .toolbar button:disabled { opacity: 0.35; cursor: default; }

  .icon-btn {
    width: 30px; height: 30px;
    border: none; border-radius: 4px; background: transparent;
    color: #999; cursor: pointer; font-size: 15px;
    display: flex; align-items: center; justify-content: center; padding: 0;
    flex-shrink: 0; text-decoration: none;
  }
  .icon-btn:hover:not(:disabled) { background: #2a2a4a; color: #eee; }
  .icon-btn.active { background: #2a2a5a; color: #aaf; }
  .icon-btn.save-btn { color: #4c9; }
  .icon-btn.save-btn:hover:not(:disabled) { background: #1a3a2a; color: #6eb; }
  .icon-btn.save-btn.saved { color: #2a6; }
  .icon-btn.save-btn.save-error { color: #f44; }
  .icon-btn:disabled { opacity: 0.5; cursor: default; }
  .new-chore-btn { color: #4c9; font-size: 18px; font-weight: 600; }
  .new-chore-btn:hover { background: #1a3a2a; color: #6eb; }

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
</style>
