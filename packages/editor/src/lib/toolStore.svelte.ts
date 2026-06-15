import type { Point } from "@myhome/geometry";

export type ToolType = "select" | "wall" | "divider";

export interface ToolState {
  tool: ToolType;
  selectedId: string | null;
  drawPoints: Point[];
  cursorWorld: Point | null;
  draggingPoint: Point | null;
}

export function createToolStore() {
  const state = $state<ToolState>({
    tool: "select",
    selectedId: null,
    drawPoints: [],
    cursorWorld: null,
    draggingPoint: null,
  });

  function setTool(tool: ToolType): void {
    state.tool = tool;
    state.selectedId = null;
    state.drawPoints = [];
    state.cursorWorld = null;
    state.draggingPoint = null;
  }

  function select(id: string | null): void {
    state.selectedId = id;
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
  }

  return {
    get state() {
      return state;
    },
    setTool,
    select,
    addDrawPoint,
    setCursor,
    resetDraw,
    startDrag,
    updateDragPoint,
    endDrag,
  };
}
