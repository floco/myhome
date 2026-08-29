import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import TableEditorModal from "../src/lib/components/ui/TableEditorModal.svelte";
import type { ParsedTable } from "../src/lib/components/ui/markdownTable";

function setup(initial: ParsedTable | null) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const onCancel = vi.fn();
  const onConfirm = vi.fn();
  const app = mount(TableEditorModal, { target, props: { initial, onCancel, onConfirm } });
  flushSync();
  return { target, app, onCancel, onConfirm };
}

function headerInputs(target: HTMLElement): HTMLInputElement[] {
  return [...target.querySelectorAll(".te-header-input")] as HTMLInputElement[];
}

function dataRows(target: HTMLElement): HTMLElement[] {
  return [...target.querySelectorAll(".te-data-row")] as HTMLElement[];
}

function rowCellValues(target: HTMLElement, ri: number): string[] {
  return [...dataRows(target)[ri].querySelectorAll(".te-cell")].map((el) => (el as HTMLInputElement).value);
}

function openRowMenu(target: HTMLElement, ri: number): void {
  (dataRows(target)[ri].querySelector(".te-row-menu-btn") as HTMLButtonElement).click();
  flushSync();
}

function openColumnMenu(target: HTMLElement, ci: number): void {
  (target.querySelectorAll(".te-col-menu-btn")[ci] as HTMLButtonElement).click();
  flushSync();
}

function menuItem(selector: string): HTMLButtonElement {
  return document.querySelector(selector) as HTMLButtonElement;
}

describe("TableEditorModal — new table", () => {
  it("shows the insert-table title and a blank 3x3 starter grid", () => {
    const { target, app } = setup(null);
    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Insert table");
    expect(headerInputs(target)).toHaveLength(3);
    expect(dataRows(target)).toHaveLength(2);
    expect(headerInputs(target).every((i) => i.value === "")).toBe(true);
    unmount(app);
    target.remove();
  });

  it("adds a column to the header and every existing row", () => {
    const { target, app } = setup(null);
    (target.querySelector(".te-add-column") as HTMLButtonElement).click();
    flushSync();
    expect(headerInputs(target)).toHaveLength(4);
    const firstRowCells = dataRows(target)[0].querySelectorAll(".te-cell");
    expect(firstRowCells).toHaveLength(4);
    unmount(app);
    target.remove();
  });

  it("adds a row with one blank cell per existing column", () => {
    const { target, app } = setup(null);
    (target.querySelector(".te-add-row") as HTMLButtonElement).click();
    flushSync();
    expect(dataRows(target)).toHaveLength(3);
    expect(dataRows(target)[2].querySelectorAll(".te-cell")).toHaveLength(3);
    unmount(app);
    target.remove();
  });

  it("calls onConfirm with typed header text, default left alignment and typed cell text", () => {
    const { target, app, onConfirm } = setup(null);
    headerInputs(target)[0].value = "Name";
    headerInputs(target)[0].dispatchEvent(new Event("input", { bubbles: true }));
    const firstCell = dataRows(target)[0].querySelector(".te-cell") as HTMLInputElement;
    firstCell.value = "Apples";
    firstCell.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    target.querySelector(".ui-modal-footer .ui-button-primary")!.dispatchEvent(new Event("click", { bubbles: true }));
    expect(onConfirm).toHaveBeenCalledOnce();
    const [headerCells, alignments, rows] = onConfirm.mock.calls[0];
    expect(headerCells[0]).toBe("Name");
    expect(alignments).toEqual(["left", "left", "left"]);
    expect(rows[0][0]).toBe("Apples");
    unmount(app);
    target.remove();
  });

  it("calls onCancel when Cancel is clicked", () => {
    const { target, app, onCancel } = setup(null);
    target.querySelector(".ui-modal-footer .ui-button-secondary")!.dispatchEvent(new Event("click", { bubbles: true }));
    expect(onCancel).toHaveBeenCalledOnce();
    unmount(app);
    target.remove();
  });
});

describe("TableEditorModal — row menu", () => {
  const initial: ParsedTable = {
    startIndex: 0,
    endIndex: 0,
    headerCells: ["A", "B", "C"],
    alignments: ["left", "left", "left"],
    rows: [
      ["r1a", "r1b", "r1c"],
      ["r2a", "r2b", "r2c"],
    ],
  };

  it("opens a menu with move, insert and delete actions", () => {
    const { target, app } = setup(initial);
    openRowMenu(target, 0);
    expect(menuItem(".te-menu-move-up")).not.toBeNull();
    expect(menuItem(".te-menu-move-down")).not.toBeNull();
    expect(menuItem(".te-menu-insert-above")).not.toBeNull();
    expect(menuItem(".te-menu-insert-below")).not.toBeNull();
    expect(menuItem(".te-menu-delete-row")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("disables move-up on the first row and move-down on the last row", () => {
    const { target, app } = setup(initial);
    openRowMenu(target, 0);
    expect(menuItem(".te-menu-move-up").disabled).toBe(true);
    expect(menuItem(".te-menu-move-down").disabled).toBe(false);
    openRowMenu(target, 1);
    expect(menuItem(".te-menu-move-down").disabled).toBe(true);
    unmount(app);
    target.remove();
  });

  it("Move down swaps the row with the one below and closes the menu", () => {
    const { target, app } = setup(initial);
    openRowMenu(target, 0);
    menuItem(".te-menu-move-down").click();
    flushSync();
    expect(rowCellValues(target, 0)).toEqual(["r2a", "r2b", "r2c"]);
    expect(rowCellValues(target, 1)).toEqual(["r1a", "r1b", "r1c"]);
    expect(document.querySelector(".te-menu-move-down")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("Insert above adds a blank row above that row", () => {
    const { target, app } = setup(initial);
    openRowMenu(target, 1);
    menuItem(".te-menu-insert-above").click();
    flushSync();
    expect(dataRows(target)).toHaveLength(3);
    expect(rowCellValues(target, 1)).toEqual(["", "", ""]);
    expect(rowCellValues(target, 2)).toEqual(["r2a", "r2b", "r2c"]);
    unmount(app);
    target.remove();
  });

  it("Insert below adds a blank row below that row", () => {
    const { target, app } = setup(initial);
    openRowMenu(target, 0);
    menuItem(".te-menu-insert-below").click();
    flushSync();
    expect(dataRows(target)).toHaveLength(3);
    expect(rowCellValues(target, 0)).toEqual(["r1a", "r1b", "r1c"]);
    expect(rowCellValues(target, 1)).toEqual(["", "", ""]);
    unmount(app);
    target.remove();
  });

  it("Delete row removes that row", () => {
    const { target, app } = setup(initial);
    openRowMenu(target, 0);
    menuItem(".te-menu-delete-row").click();
    flushSync();
    expect(dataRows(target)).toHaveLength(1);
    expect(rowCellValues(target, 0)).toEqual(["r2a", "r2b", "r2c"]);
    unmount(app);
    target.remove();
  });
});

describe("TableEditorModal — column menu", () => {
  const initial: ParsedTable = {
    startIndex: 0,
    endIndex: 0,
    headerCells: ["A", "B", "C"],
    alignments: ["left", "left", "left"],
    rows: [["r1a", "r1b", "r1c"]],
  };

  it("opens a menu with align, move, insert and delete actions", () => {
    const { target, app } = setup(initial);
    openColumnMenu(target, 0);
    expect(menuItem(".te-menu-align-left")).not.toBeNull();
    expect(menuItem(".te-menu-align-center")).not.toBeNull();
    expect(menuItem(".te-menu-align-right")).not.toBeNull();
    expect(menuItem(".te-menu-move-left")).not.toBeNull();
    expect(menuItem(".te-menu-move-right")).not.toBeNull();
    expect(menuItem(".te-menu-insert-left")).not.toBeNull();
    expect(menuItem(".te-menu-insert-right")).not.toBeNull();
    expect(menuItem(".te-menu-delete-column")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("disables move-left on the first column and move-right on the last column", () => {
    const { target, app } = setup(initial);
    openColumnMenu(target, 0);
    expect(menuItem(".te-menu-move-left").disabled).toBe(true);
    openColumnMenu(target, 2);
    expect(menuItem(".te-menu-move-right").disabled).toBe(true);
    unmount(app);
    target.remove();
  });

  it("disables delete when only one column remains", () => {
    const { target, app } = setup({ ...initial, headerCells: ["Only"], alignments: ["left"], rows: [["x"]] });
    openColumnMenu(target, 0);
    expect(menuItem(".te-menu-delete-column").disabled).toBe(true);
    unmount(app);
    target.remove();
  });

  it("selecting an alignment updates it and closes the menu", () => {
    const { target, app, onConfirm } = setup(initial);
    openColumnMenu(target, 0);
    menuItem(".te-menu-align-center").click();
    flushSync();
    expect(document.querySelector(".te-menu-align-center")).toBeNull();
    target.querySelector(".ui-modal-footer .ui-button-primary")!.dispatchEvent(new Event("click", { bubbles: true }));
    const [, alignments] = onConfirm.mock.calls[0];
    expect(alignments[0]).toBe("center");
    unmount(app);
    target.remove();
  });

  it("Move right swaps header, alignment and every row's cell with the next column", () => {
    const { target, app, onConfirm } = setup(initial);
    openColumnMenu(target, 1);
    menuItem(".te-menu-align-center").click();
    flushSync();
    openColumnMenu(target, 0);
    menuItem(".te-menu-move-right").click();
    flushSync();
    expect(headerInputs(target).map((i) => i.value)).toEqual(["B", "A", "C"]);
    expect(rowCellValues(target, 0)).toEqual(["r1b", "r1a", "r1c"]);
    target.querySelector(".ui-modal-footer .ui-button-primary")!.dispatchEvent(new Event("click", { bubbles: true }));
    const [, alignments] = onConfirm.mock.calls[0];
    expect(alignments).toEqual(["center", "left", "left"]);
    unmount(app);
    target.remove();
  });

  it("Insert left adds a blank column to the left of that column", () => {
    const { target, app } = setup(initial);
    openColumnMenu(target, 1);
    menuItem(".te-menu-insert-left").click();
    flushSync();
    expect(headerInputs(target).map((i) => i.value)).toEqual(["A", "", "B", "C"]);
    expect(rowCellValues(target, 0)).toEqual(["r1a", "", "r1b", "r1c"]);
    unmount(app);
    target.remove();
  });

  it("Insert right adds a blank column to the right of that column", () => {
    const { target, app } = setup(initial);
    openColumnMenu(target, 0);
    menuItem(".te-menu-insert-right").click();
    flushSync();
    expect(headerInputs(target).map((i) => i.value)).toEqual(["A", "", "B", "C"]);
    expect(rowCellValues(target, 0)).toEqual(["r1a", "", "r1b", "r1c"]);
    unmount(app);
    target.remove();
  });

  it("Delete column removes that column from header and all rows", () => {
    const { target, app } = setup(initial);
    openColumnMenu(target, 0);
    menuItem(".te-menu-delete-column").click();
    flushSync();
    expect(headerInputs(target).map((i) => i.value)).toEqual(["B", "C"]);
    expect(rowCellValues(target, 0)).toEqual(["r1b", "r1c"]);
    unmount(app);
    target.remove();
  });
});

describe("TableEditorModal — editing an existing table", () => {
  const initial: ParsedTable = {
    startIndex: 0,
    endIndex: 0,
    headerCells: ["Name", "Qty"],
    alignments: ["left", "right"],
    rows: [["Apples", "3"]],
  };

  it("shows the edit-table title and pre-fills the grid from initial data", () => {
    const { target, app } = setup(initial);
    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit table");
    const headers = headerInputs(target);
    expect(headers.map((i) => i.value)).toEqual(["Name", "Qty"]);
    const firstRowCells = dataRows(target)[0].querySelectorAll(".te-cell") as unknown as HTMLInputElement[];
    expect([...firstRowCells].map((i) => i.value)).toEqual(["Apples", "3"]);
    unmount(app);
    target.remove();
  });

  it("passes through the existing alignments unchanged when confirmed without edits", () => {
    const { target, app, onConfirm } = setup(initial);
    target.querySelector(".ui-modal-footer .ui-button-primary")!.dispatchEvent(new Event("click", { bubbles: true }));
    const [headerCells, alignments, rows] = onConfirm.mock.calls[0];
    expect(headerCells).toEqual(["Name", "Qty"]);
    expect(alignments).toEqual(["left", "right"]);
    expect(rows).toEqual([["Apples", "3"]]);
    unmount(app);
    target.remove();
  });
});
