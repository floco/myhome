<script lang="ts">
  import type { Floor, Point } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte";
  import type { ToolType } from "../toolStore.svelte";
  import { computeSnap, allEndpoints } from "../drawingTool";
  import { SNAP_RADIUS_PX } from "../geometry-helpers";
  import Grid from "./Grid.svelte";
  import WallShape from "./WallShape.svelte";
  import DividerShape from "./DividerShape.svelte";
  import RoomShape from "./RoomShape.svelte";
  import DrawPreview from "./DrawPreview.svelte";
  import SelectionHandles from "./SelectionHandles.svelte";

  let {
    floor,
    viewport,
    width,
    height,
    selectedId = null,
    onselect,
    tool = "select",
    drawPoints = [],
    cursorWorld = null,
    spacePressed = false,
    onpointermove,
    onplacepoint,
    ondblclick,
    ondragstart,
    ondragend,
    onpan,
    onzoom,
  }: {
    floor: Floor;
    viewport: ViewportState;
    width: number;
    height: number;
    selectedId?: string | null;
    onselect?: (id: string | null) => void;
    tool?: ToolType;
    drawPoints?: Point[];
    cursorWorld?: Point | null;
    spacePressed?: boolean;
    onpointermove?: (point: Point) => void;
    onplacepoint?: (point: Point) => void;
    ondblclick?: () => void;
    ondragstart?: (point: Point) => void;
    ondragend?: () => void;
    onpan?: (dx: number, dy: number) => void;
    onzoom?: (screen: Point, factor: number) => void;
  } = $props();

  const snapResult = $derived.by(() => {
    if (tool === "select" || !cursorWorld) return null;
    const radius = SNAP_RADIUS_PX / viewport.zoom;
    return computeSnap(cursorWorld, allEndpoints(floor.walls), drawPoints, radius);
  });

  const selectedWall = $derived(floor.walls.find((w) => w.id === selectedId) ?? null);

  let panState = $state<Point | null>(null);
  let suppressNextClick = false; // not reactive: consumed synchronously by the next onclick
  let lastClickPos: { x: number; y: number } | null = null;
  let clickCountResetTimer: ReturnType<typeof setTimeout> | null = null;

  function toWorld(event: MouseEvent): Point {
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    return {
      x: (event.clientX - rect.left - viewport.panX) / viewport.zoom,
      y: (event.clientY - rect.top - viewport.panY) / viewport.zoom,
    };
  }

  function handleMouseDown(event: MouseEvent): void {
    if (event.button === 1 || (event.button === 0 && spacePressed)) {
      event.preventDefault();
      panState = { x: event.clientX, y: event.clientY };
      suppressNextClick = true;
    }
  }

  function handleMouseMove(event: MouseEvent): void {
    if (panState) {
      const dx = event.clientX - panState.x;
      const dy = event.clientY - panState.y;
      onpan?.(dx, dy);
      panState = { x: event.clientX, y: event.clientY };
      return;
    }
    onpointermove?.(toWorld(event));
  }

  function handleMouseUp(): void {
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
      return;
    }
    if (snapResult) onplacepoint?.(snapResult.point);
  }

  function handleDragStart(point: Point, event: MouseEvent): void {
    event.stopPropagation();
    ondragstart?.(point);
  }
</script>

<svg
  {width}
  {height}
  class="canvas"
  onclick={handleClick}
  onmousedown={handleMouseDown}
  onmousemove={handleMouseMove}
  onmouseup={handleMouseUp}
  ondblclick={() => ondblclick?.()}
  onwheel={handleWheel}
>
  <Grid {viewport} {width} {height} />
  {#each floor.rooms as room (room.id)}
    <RoomShape {room} {viewport} />
  {/each}
  {#each floor.walls as wall (wall.id)}
    {#if wall.type === "wall"}
      <WallShape {wall} {viewport} {tool} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {:else}
      <DividerShape {wall} {viewport} {tool} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {/if}
  {/each}
  {#if tool !== "select"}
    <DrawPreview
      chainPoints={drawPoints}
      snapPoint={snapResult?.point ?? null}
      showSnapRing={snapResult ? snapResult.snappedToExisting || snapResult.closesLoop : false}
      {viewport}
    />
  {/if}
  {#if selectedWall}
    <SelectionHandles wall={selectedWall} {viewport} ondragstart={handleDragStart} />
  {/if}
</svg>

<style>
  .canvas {
    background: #1c1c1c;
    display: block;
  }
</style>
