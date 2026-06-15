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
    onpointermove,
    onplacepoint,
    ondblclick,
    ondragstart,
    ondragend,
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
    onpointermove?: (point: Point) => void;
    onplacepoint?: (point: Point) => void;
    ondblclick?: () => void;
    ondragstart?: (point: Point) => void;
    ondragend?: () => void;
  } = $props();

  const snapResult = $derived.by(() => {
    if (tool === "select" || !cursorWorld) return null;
    const radius = SNAP_RADIUS_PX / viewport.zoom;
    return computeSnap(cursorWorld, allEndpoints(floor.walls), drawPoints, radius);
  });

  const selectedWall = $derived(floor.walls.find((w) => w.id === selectedId) ?? null);

  function toWorld(event: MouseEvent): Point {
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    return {
      x: (event.clientX - rect.left - viewport.panX) / viewport.zoom,
      y: (event.clientY - rect.top - viewport.panY) / viewport.zoom,
    };
  }

  function handleMouseMove(event: MouseEvent): void {
    onpointermove?.(toWorld(event));
  }

  function handleMouseUp(): void {
    ondragend?.();
  }

  function handleDragStart(point: Point, event: MouseEvent): void {
    event.stopPropagation();
    ondragstart?.(point);
  }

  function handleClick(): void {
    if (tool === "select") {
      onselect?.(null);
      return;
    }
    if (snapResult) onplacepoint?.(snapResult.point);
  }
</script>

<svg
  {width}
  {height}
  class="canvas"
  onclick={handleClick}
  onmousemove={handleMouseMove}
  onmouseup={handleMouseUp}
  ondblclick={() => ondblclick?.()}
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
