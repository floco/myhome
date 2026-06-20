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
  import ChorePanel from "./lib/components/ChorePanel.svelte";
  import BadgePopup from "./lib/components/BadgePopup.svelte";
  import ChoresPage from "./lib/components/ChoresPage.svelte";
  import ChoreListPage from "./lib/components/ChoreListPage.svelte";
  import NavMenu from "./lib/components/NavMenu.svelte";
  import NewChoreModal from "./lib/components/NewChoreModal.svelte";
  import InventoryPage from "./lib/components/InventoryPage.svelte";
  import ConsumablesPage from "./lib/components/ConsumablesPage.svelte";
  import WorksPage from "./lib/components/WorksPage.svelte";
  import FinancePage from "./lib/components/FinancePage.svelte";

  const floorStore = createHouseStore();
  const viewportStore = createViewportStore();
  const toolStore = createToolStore();
  const choreStore = createChoreStore();

  let choreMode = $state(false);
  let draggingChoreId = $state<string | null>(null);
  let selectedBadge = $state<{ assignment: Assignment; screenX: number; screenY: number } | null>(null);
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
    if (event.key === "Escape") { toolStore.resetDraw(); return; }
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
    if (!draggingChoreId) return;
    e.preventDefault();
  }

  function handleDrop(e: DragEvent): void {
    const choreId = e.dataTransfer?.getData("choreId") ?? draggingChoreId;
    draggingChoreId = null;
    if (!choreId) return;
    e.preventDefault();
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const screenX = e.clientX - rect.left, screenY = e.clientY - rect.top;
    const worldX = (screenX - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
    const worldY = (screenY - viewportStore.viewport.panY) / viewportStore.viewport.zoom;
    const room = floorStore.floor.rooms.find((r) => {
      if (!r.polygon) return false;
      return pointInPolygon({ x: worldX, y: worldY }, r.polygon);
    });
    if (!room) return;
    const chore = choreStore.chores.find((c) => c.id === choreId);
    choreStore.createAssignment({ choreId, roomId: room.id, position: { x: worldX, y: worldY }, nextDueDate: chore?.nextDueDate ?? "" });
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
        currentFloorId={floorStore.currentFloorId}
        onswitchfloor={(id) => { floorStore.switchFloor(id); toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null); }}
        onaddfloor={(name) => floorStore.addFloor(name)}
        onrenamefloor={(id, name) => floorStore.renameFloor(id, name)}
        onremovefloor={(id) => floorStore.removeFloor(id)}
      />

      <span class="spacer"></span>

      {#if !choreMode}
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

      <button
        class="icon-btn"
        class:active={choreMode}
        title="Chore picker"
        onclick={() => { choreMode = !choreMode; if (choreMode) toolStore.setTool("select"); else selectedBadge = null; }}
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
            <ChoreOverlay
              chores={choreStore.chores}
              assignments={currentFloorAssignments}
              viewport={viewportStore.viewport}
              {choreMode}
              width={canvasWidth}
              height={canvasHeight}
              onclick={(id) => handleBadgeClick(id)}
              ondragend={handleBadgeDragEnd}
            />
            {#if choreMode}
              <ChorePanel
                store={choreStore}
                {draggingChoreId}
                onDragStart={(id) => { draggingChoreId = id; }}
                onDragEnd={() => { draggingChoreId = null; }}
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
          {/if}
        </div>

      {:else if currentRoute === "#/chores"}
        <ChoreListPage store={choreStore} {floorStore} />

      {:else if currentRoute === "#/chores/manage"}
        <ChoresPage store={choreStore} {floorStore} onnewchore={() => { showNewChoreModal = true; }} />

      {:else if currentRoute === "#/inventory"}
        <InventoryPage />

      {:else if currentRoute === "#/consumables"}
        <ConsumablesPage />

      {:else if currentRoute === "#/works"}
        <WorksPage />

      {:else if currentRoute === "#/finance"}
        <FinancePage />
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

  .loading {
    display: flex; align-items: center; justify-content: center;
    height: 100%; color: #888; font-size: 14px;
  }
</style>
