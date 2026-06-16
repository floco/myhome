<script lang="ts">
  import type { Point, WallType } from "@myhome/geometry";
  import { pointsEqual } from "@myhome/geometry";
  import { createFloorStore } from "./lib/floorStore.svelte";
  import { createViewportStore } from "./lib/viewportStore.svelte";
  import { createToolStore } from "./lib/toolStore.svelte";
  import { placePoint, allEndpoints } from "./lib/drawingTool";
  import { findSnapPoint, snapToGrid, SNAP_RADIUS_PX } from "./lib/geometry-helpers";
  import Canvas from "./lib/components/Canvas.svelte";
  import Toolbar from "./lib/components/Toolbar.svelte";

  const floorStore = createFloorStore();
  const viewportStore = createViewportStore();
  const toolStore = createToolStore();

  let spacePressed = $state(false);

  function handleSelect(id: string | null): void {
    if (toolStore.state.tool === "select") {
      toolStore.select(id);
    }
  }

  function handleDelete(): void {
    const id = toolStore.state.selectedId;
    if (id) {
      floorStore.removeWall(id);
      toolStore.select(null);
    }
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

    floorStore.moveSharedPoint(dragging, snapped);
    toolStore.updateDragPoint(snapped);
  }

  function handlePointerMove(world: Point): void {
    toolStore.setCursor(world);
    if (toolStore.state.draggingPoint) {
      handleDragMove(world);
    }
  }

  function handlePlacePoint(point: Point): void {
    const tool = toolStore.state.tool;
    if (tool === "select") return;

    const chain = toolStore.state.drawPoints;
    if (chain.length === 0) {
      toolStore.addDrawPoint(point);
      return;
    }

    const { segment, chainEnds } = placePoint(chain, point, tool as WallType, () =>
      crypto.randomUUID(),
    );
    if (segment) {
      floorStore.addWall(segment);
      toolStore.addDrawPoint(point);
    }
    if (chainEnds) {
      toolStore.resetDraw();
    }
  }

  function handleDragStart(point: Point): void {
    toolStore.startDrag(point);
  }

  function handleDragEnd(): void {
    toolStore.endDrag();
  }

  function handlePan(dx: number, dy: number): void {
    viewportStore.pan(dx, dy);
  }

  function handleZoom(screen: Point, factor: number): void {
    viewportStore.zoomAt(screen, factor);
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.code === "Space") {
      spacePressed = true;
      return;
    }
    if (event.key === "Escape") {
      toolStore.resetDraw();
      return;
    }
    if ((event.key === "Delete" || event.key === "Backspace") && toolStore.state.selectedId) {
      handleDelete();
    }
  }

  function handleKeyup(event: KeyboardEvent): void {
    if (event.code === "Space") {
      spacePressed = false;
    }
  }
</script>

<svelte:window
  onkeydown={handleKeydown}
  onkeyup={handleKeyup}
  onblur={() => { spacePressed = false; }}
/>

<div class="app">
  <header class="topbar">
    <h1>Floor Plan Editor</h1>
    <button class="reset-view" onclick={() => viewportStore.reset()}>Reset View</button>
  </header>
  <div class="body">
    <Toolbar
      tool={toolStore.state.tool}
      hasSelection={toolStore.state.selectedId !== null}
      onselecttool={(tool) => toolStore.setTool(tool)}
      ondelete={handleDelete}
    />
    <Canvas
      floor={floorStore.floor}
      viewport={viewportStore.viewport}
      width={1200}
      height={800}
      selectedId={toolStore.state.selectedId}
      onselect={handleSelect}
      tool={toolStore.state.tool}
      drawPoints={toolStore.state.drawPoints}
      cursorWorld={toolStore.state.cursorWorld}
      {spacePressed}
      onpointermove={handlePointerMove}
      onplacepoint={handlePlacePoint}
      ondblclick={() => toolStore.resetDraw()}
      ondragstart={handleDragStart}
      ondragend={handleDragEnd}
      onpan={handlePan}
      onzoom={handleZoom}
    />
  </div>
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    font-family: sans-serif;
  }
  .topbar {
    height: 32px;
    background: #2a2a2a;
    color: #ccc;
    display: flex;
    align-items: center;
    padding: 0 12px;
    flex-shrink: 0;
    justify-content: space-between;
  }
  .topbar h1 {
    font-size: 14px;
    margin: 0;
    font-weight: 600;
  }
  .reset-view {
    padding: 4px 10px;
    border: none;
    border-radius: 4px;
    background: #444;
    color: #ccc;
    cursor: pointer;
  }
  .body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
</style>
