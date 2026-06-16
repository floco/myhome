import type { Point } from "@myhome/geometry";

export type ToolType = "select" | "wall" | "divider" | "door" | "window";

export interface ToolState {
  tool: ToolType;
  selectedId: string | null;
  selectedRoomId: string | null;
  selectedOpeningId: string | null;
  drawPoints: Point[];
  cursorWorld: Point | null;
  draggingPoint: Point | null;
  draggingOpeningHandle: { openingId: string; side: "start" | "end" } | null;
}

export function createToolStore() {
  const state = $state<ToolState>({
    tool: "select",
    selectedId: null,
    selectedRoomId: null,
    selectedOpeningId: null,
    drawPoints: [],
    cursorWorld: null,
    draggingPoint: null,
    draggingOpeningHandle: null,
  });

  function setTool(tool: ToolType): void {
    state.tool = tool;
    state.selectedId = null;
    state.selectedRoomId = null;
    state.selectedOpeningId = null;
    state.drawPoints = [];
    state.cursorWorld = null;
    state.draggingPoint = null;
    state.draggingOpeningHandle = null;
  }

  function select(id: string | null): void {
    state.selectedId = id;
    state.selectedRoomId = null;
    state.selectedOpeningId = null;
  }

  function selectRoom(id: string | null): void {
    state.selectedRoomId = id;
    state.selectedId = null;
    state.selectedOpeningId = null;
  }

  function selectOpening(id: string | null): void {
    state.selectedOpeningId = id;
    state.selectedId = null;
    state.selectedRoomId = null;
  }

  function addDrawPoint(p: Point): void {
    state.drawPoints.push(p);
  }

  function setCursor(p: Point | null): void {
    state.cursorWorld = p;
  }

  function resetDraw(): void {
    state.drawPoints = [];
  }

  function startDrag(point: Point): void {
    state.draggingPoint = point;
  }

  function updateDragPoint(point: Point): void {
    state.draggingPoint = point;
  }

  function endDrag(): void {
    state.draggingPoint = null;
    state.draggingOpeningHandle = null;
  }

  function startOpeningDrag(openingId: string, side: "start" | "end"): void {
    state.draggingOpeningHandle = { openingId, side };
  }

  function endOpeningDrag(): void {
    state.draggingOpeningHandle = null;
  }

  return {
    get state() {
      return state;
    },
    setTool,
    select,
    selectRoom,
    selectOpening,
    addDrawPoint,
    setCursor,
    resetDraw,
    startDrag,
    updateDragPoint,
    endDrag,
    startOpeningDrag,
    endOpeningDrag,
  };
}
