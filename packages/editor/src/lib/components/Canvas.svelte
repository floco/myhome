<script lang="ts">
  import type { Floor, Point, FurnitureObject } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte.ts";
  import type { ToolType } from "../toolStore.svelte";
  import type { HaEntityState } from "../haStateStore.svelte";
  import { computeSnap, allEndpoints } from "../drawingTool";
  import { SNAP_RADIUS_PX, hitTestWall, HIT_RADIUS_PX, findAdjacentWall } from "../geometry-helpers";
  import { worldToScreen } from "../viewportStore.svelte.ts";
  import { getTemplate } from "../furnitureLibrary";
  import Grid from "./Grid.svelte";
  import WallShape from "./WallShape.svelte";
  import DividerShape from "./DividerShape.svelte";
  import RoomShape from "./RoomShape.svelte";
  import DrawPreview from "./DrawPreview.svelte";
  import SelectionHandles from "./SelectionHandles.svelte";
  import OpeningShape from "./OpeningShape.svelte";
  import FurnitureShape from "./FurnitureShape.svelte";
  import FurnitureHandles from "./FurnitureHandles.svelte";

  let {
    floor,
    viewport,
    width,
    height,
    selectedId = null,
    selectedRoomId = null,
    selectedOpeningId = null,
    selectedFurnitureId = null,
    furnitureObjects = [],
    onselect,
    onselectroom,
    onselectopening,
    ondragopeninghandlestart,
    onselectfurniture,
    onmovefurniturestart,
    onresizefurniturestart,
    onrotatefurniturestart,
    tool = "select",
    showGrid = true,
    drawPoints = [],
    cursorWorld = null,
    spacePressed = false,
    draggingPoint = null,
    onpointermove,
    onplacepoint,
    ondblclick,
    ondragstart,
    ondragend,
    onpan,
    onzoom,
    haLayerActive = false,
    haStates = new Map<string, HaEntityState>(),
  }: {
    floor: Floor;
    viewport: ViewportState;
    width: number;
    height: number;
    selectedId?: string | null;
    selectedRoomId?: string | null;
    selectedOpeningId?: string | null;
    selectedFurnitureId?: string | null;
    furnitureObjects?: FurnitureObject[];
    onselect?: (id: string | null) => void;
    onselectroom?: (id: string | null) => void;
    onselectopening?: (id: string | null) => void;
    ondragopeninghandlestart?: (openingId: string, side: "start" | "end") => void;
    onselectfurniture?: (id: string | null) => void;
    onmovefurniturestart?: (id: string, e: MouseEvent) => void;
    onresizefurniturestart?: (id: string, corner: string, e: MouseEvent) => void;
    onrotatefurniturestart?: (id: string, e: MouseEvent) => void;
    tool?: ToolType;
    showGrid?: boolean;
    drawPoints?: Point[];
    cursorWorld?: Point | null;
    spacePressed?: boolean;
    draggingPoint?: Point | null;
    onpointermove?: (point: Point) => void;
    onplacepoint?: (point: Point) => void;
    ondblclick?: () => void;
    ondragstart?: (point: Point) => void;
    ondragend?: () => void;
    onpan?: (dx: number, dy: number) => void;
    onzoom?: (screen: Point, factor: number) => void;
    haLayerActive?: boolean;
    haStates?: Map<string, HaEntityState>;
  } = $props();

  const snapResult = $derived.by(() => {
    if (tool !== "wall" && tool !== "divider") return null;
    if (!cursorWorld) return null;
    const radius = SNAP_RADIUS_PX / viewport.zoom;
    return computeSnap(cursorWorld, allEndpoints(floor.walls), drawPoints, radius);
  });

  const wallHit = $derived.by(() => {
    if (tool !== "door" && tool !== "window") return null;
    if (!cursorWorld) return null;
    return hitTestWall(cursorWorld, floor.walls, HIT_RADIUS_PX / viewport.zoom);
  });

  const openingPreview = $derived.by(() => {
    if (!wallHit) return null;
    const { wall, offset } = wallHit;
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const len = Math.hypot(dx, dy);
    if (len < 1e-9) return null;
    const dirX = dx / len;
    const dirY = dy / len;
    const defaultWidth = tool === "door" ? 0.9 : 1.2;
    const clampedWidth = Math.min(defaultWidth, len - offset);
    if (clampedWidth < 1e-9) return null;
    const wp1 = { x: wall.start.x + dirX * offset, y: wall.start.y + dirY * offset };
    const wp2 = { x: wall.start.x + dirX * (offset + clampedWidth), y: wall.start.y + dirY * (offset + clampedWidth) };
    return { sp1: worldToScreen(wp1, viewport), sp2: worldToScreen(wp2, viewport) };
  });

  const selectedWall = $derived(floor.walls.find((w) => w.id === selectedId) ?? null);

  let panState = $state<Point | null>(null);
  let suppressNextClick = false; // not reactive: consumed synchronously by the next onclick
  let lastClickPos: { x: number; y: number } | null = null;
  let clickCountResetTimer: ReturnType<typeof setTimeout> | null = null;

  const activePointers = new Map<number, Point>();
  let gestureBase: { centroid: Point; distance: number } | null = null;

  function gesturePoints(): Point[] {
    return [...activePointers.values()].slice(0, 2);
  }

  function centroidOf(pts: Point[]): Point {
    return { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 };
  }

  function distanceOf(pts: Point[]): number {
    return Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
  }

  function rebaseGesture(): void {
    const pts = gesturePoints();
    gestureBase = pts.length >= 2 ? { centroid: centroidOf(pts), distance: distanceOf(pts) } : null;
  }

  function toWorld(event: PointerEvent): Point {
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    return {
      x: (event.clientX - rect.left - viewport.panX) / viewport.zoom,
      y: (event.clientY - rect.top - viewport.panY) / viewport.zoom,
    };
  }

  function handlePointerDown(event: PointerEvent): void {
    activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (activePointers.size >= 2) {
      rebaseGesture();
      panState = null;
      suppressNextClick = true;
      return;
    }
    if (event.button === 1 || (event.button === 0 && spacePressed)) {
      event.preventDefault();
      panState = { x: event.clientX, y: event.clientY };
      suppressNextClick = true;
    }
  }

  function handlePointerMove(event: PointerEvent): void {
    if (activePointers.has(event.pointerId)) {
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }
    if (activePointers.size >= 2) {
      const pts = gesturePoints();
      const centroid = centroidOf(pts);
      const dist = distanceOf(pts);
      if (gestureBase) {
        const dx = centroid.x - gestureBase.centroid.x;
        const dy = centroid.y - gestureBase.centroid.y;
        if (dx !== 0 || dy !== 0) onpan?.(dx, dy);
        if (gestureBase.distance > 0 && dist > 0) {
          const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
          onzoom?.({ x: centroid.x - rect.left, y: centroid.y - rect.top }, dist / gestureBase.distance);
        }
      }
      gestureBase = { centroid, distance: dist };
      return;
    }
    if (panState) {
      const dx = event.clientX - panState.x;
      const dy = event.clientY - panState.y;
      onpan?.(dx, dy);
      panState = { x: event.clientX, y: event.clientY };
      return;
    }
    onpointermove?.(toWorld(event));
  }

  function handlePointerUp(event: PointerEvent): void {
    activePointers.delete(event.pointerId);
    rebaseGesture();
    const wasPanning = panState !== null;
    panState = null;
    if (!wasPanning) {
      ondragend?.();
    }
  }

  function handleWheel(event: WheelEvent): void {
    event.preventDefault();
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    const screen = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1;
    onzoom?.(screen, factor);
  }

  function handleClick(event: MouseEvent): void {
    const currentPos = { x: event.clientX, y: event.clientY };

    // If this click is at the same position as the previous click within a short time window,
    // it's likely the synthetic click from a browser double-click. Suppress it.
    if (
      lastClickPos &&
      lastClickPos.x === currentPos.x &&
      lastClickPos.y === currentPos.y &&
      clickCountResetTimer !== null
    ) {
      return;
    }

    // Record this click position and reset the timer
    lastClickPos = currentPos;
    if (clickCountResetTimer) {
      clearTimeout(clickCountResetTimer);
    }
    clickCountResetTimer = setTimeout(() => {
      lastClickPos = null;
      clickCountResetTimer = null;
    }, 300);

    if (suppressNextClick) {
      suppressNextClick = false;
      return;
    }
    if (tool === "select") {
      onselect?.(null);
      onselectopening?.(null);
      onselectroom?.(null);
      onselectfurniture?.(null);
      return;
    }
    if (tool === "door" || tool === "window") {
      if (wallHit && cursorWorld) onplacepoint?.(cursorWorld);
      return;
    }
    if (snapResult) onplacepoint?.(snapResult.point);
  }

  function handleDragStart(point: Point, event: PointerEvent): void {
    event.stopPropagation();
    ondragstart?.(point);
  }
</script>

<svg
  {width}
  {height}
  class="canvas"
  onclick={handleClick}
  onpointerdown={handlePointerDown}
  onpointermove={handlePointerMove}
  onpointerup={handlePointerUp}
  ondblclick={() => ondblclick?.()}
  onwheel={handleWheel}
>
  {#if showGrid}
    <Grid {viewport} {width} {height} />
  {/if}
  {#each floor.rooms as room (room.id)}
    <RoomShape
      {room}
      {viewport}
      {tool}
      selected={room.id === selectedRoomId}
      onselectroom={(id) => onselectroom?.(id)}
    />
  {/each}
  {#each furnitureObjects as object (object.id)}
    {@const template = getTemplate(object.templateId)}
    {#if template}
      <FurnitureShape
        {object}
        {template}
        {viewport}
        {tool}
        selected={object.id === selectedFurnitureId}
        onselect={(id) => onselectfurniture?.(id)}
        onbodymousedown={(id, e) => { e.stopPropagation(); onmovefurniturestart?.(id, e); }}
      />
    {/if}
  {/each}
  {#if selectedFurnitureId}
    {@const selObj = furnitureObjects.find((f) => f.id === selectedFurnitureId)}
    {#if selObj}
      <FurnitureHandles
        object={selObj}
        {viewport}
        onresizestart={(id, corner, e) => onresizefurniturestart?.(id, corner, e)}
        onrotatestart={(id, e) => onrotatefurniturestart?.(id, e)}
      />
    {/if}
  {/if}
  {#each floor.walls as wall (wall.id)}
    {#if wall.type === "wall"}
      <WallShape
          {wall}
          wallAtStart={findAdjacentWall(floor.walls, wall, false)}
          wallAtEnd={findAdjacentWall(floor.walls, wall, true)}
          {viewport}
          {tool}
          selected={wall.id === selectedId}
          onselect={(id) => onselect?.(id)}
        />
    {:else}
      <DividerShape {wall} {viewport} {tool} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {/if}
  {/each}
  {#each floor.openings as opening (opening.id)}
    {#each floor.walls.filter((w) => w.id === opening.wallId && w.type === "wall") as wall (wall.id)}
      <OpeningShape
        {wall}
        {opening}
        {viewport}
        {tool}
        selected={opening.id === selectedOpeningId}
        haLayerActive={haLayerActive}
        haState={opening.haEntityId ? (haStates.get(opening.haEntityId) ?? null) : null}
        shutterState={opening.hasShutter && opening.shutterEntityId ? (haStates.get(opening.shutterEntityId) ?? null) : null}
        onselect={(id) => onselectopening?.(id)}
        ondraghandlestart={(openingId, side, event) => {
          event.stopPropagation();
          ondragopeninghandlestart?.(openingId, side);
        }}
      />
    {/each}
  {/each}
  {#if tool === "wall" || tool === "divider"}
    <DrawPreview
      chainPoints={drawPoints}
      snapPoint={snapResult?.point ?? null}
      showSnapRing={snapResult ? snapResult.snappedToExisting || snapResult.closesLoop : false}
      {viewport}
    />
  {/if}
  {#if openingPreview}
    <line
      x1={openingPreview.sp1.x}
      y1={openingPreview.sp1.y}
      x2={openingPreview.sp2.x}
      y2={openingPreview.sp2.y}
      stroke={tool === "door" ? "var(--canvas-opening-door)" : "var(--canvas-opening-window)"}
      stroke-width="6"
      stroke-dasharray="4 2"
      opacity="0.6"
      pointer-events="none"
    />
  {/if}
  {#if selectedWall}
    <SelectionHandles wall={selectedWall} {viewport} {draggingPoint} ondragstart={handleDragStart} />
  {/if}
</svg>

<style>
  .canvas {
    background: var(--canvas-bg);
    display: block;
    touch-action: none;
  }
</style>
