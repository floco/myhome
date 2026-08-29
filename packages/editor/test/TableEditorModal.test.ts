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

  it("removes a row when its remove button is clicked", () => {
    const { target, app } = setup(null);
    (dataRows(target)[0].querySelector(".te-row-remove") as HTMLButtonElement).click();
    flushSync();
    expect(dataRows(target)).toHaveLength(1);
    unmount(app);
    target.remove();
  });

  it("removes a column from header and all rows", () => {
    const { target, app } = setup(null);
    const removeButtons = [...target.querySelectorAll(".te-col-remove")] as HTMLButtonElement[];
    removeButtons[0].click();
    flushSync();
    expect(headerInputs(target)).toHaveLength(2);
    expect(dataRows(target)[0].querySelectorAll(".te-cell")).toHaveLength(2);
    unmount(app);
    target.remove();
  });

  it("disables column removal when only one column remains", () => {
    const { target, app } = setup(null);
    const removeButtons = () => [...target.querySelectorAll(".te-col-remove")] as HTMLButtonElement[];
    removeButtons()[0].click();
    flushSync();
    removeButtons()[0].click();
    flushSync();
    expect(headerInputs(target)).toHaveLength(1);
    expect(removeButtons()[0].disabled).toBe(true);
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

  it("cycles a column's alignment through left, center and right", () => {
    const { target, app, onConfirm } = setup(null);
    const alignGroup = target.querySelectorAll(".te-align-group")[0];
    (alignGroup.querySelector('[title="Align center"]') as HTMLButtonElement).click();
    flushSync();
    target.querySelector(".ui-modal-footer .ui-button-primary")!.dispatchEvent(new Event("click", { bubbles: true }));
    const [, alignments] = onConfirm.mock.calls[0];
    expect(alignments[0]).toBe("center");
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

describe("TableEditorModal — reordering and relative insert", () => {
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

  function rowCellValues(target: HTMLElement, ri: number): string[] {
    return [...dataRows(target)[ri].querySelectorAll(".te-cell")].map((el) => (el as HTMLInputElement).value);
  }

  it("selecting a row marks it selected, and selecting it again clears the selection", () => {
    const { target, app } = setup(initial);
    const handle = dataRows(target)[0].querySelector(".te-row-handle") as HTMLButtonElement;
    handle.click();
    flushSync();
    expect(dataRows(target)[0].classList.contains("te-row-selected")).toBe(true);
    handle.click();
    flushSync();
    expect(dataRows(target)[0].classList.contains("te-row-selected")).toBe(false);
    unmount(app);
    target.remove();
  });

  it("selecting a column marks its header cell selected", () => {
    const { target, app } = setup(initial);
    const handle = target.querySelectorAll(".te-col-handle")[1] as HTMLButtonElement;
    handle.click();
    flushSync();
    const toolbarCell = handle.closest("th") as HTMLElement;
    expect(toolbarCell.classList.contains("te-col-selected")).toBe(true);
    unmount(app);
    target.remove();
  });

  it("moving a row down swaps it with the row below", () => {
    const { target, app } = setup(initial);
    (dataRows(target)[0].querySelector(".te-row-move-down") as HTMLButtonElement).click();
    flushSync();
    expect(rowCellValues(target, 0)).toEqual(["r2a", "r2b", "r2c"]);
    expect(rowCellValues(target, 1)).toEqual(["r1a", "r1b", "r1c"]);
    unmount(app);
    target.remove();
  });

  it("disables moving the first row up and the last row down", () => {
    const { target, app } = setup(initial);
    expect((dataRows(target)[0].querySelector(".te-row-move-up") as HTMLButtonElement).disabled).toBe(true);
    expect((dataRows(target)[1].querySelector(".te-row-move-down") as HTMLButtonElement).disabled).toBe(true);
    unmount(app);
    target.remove();
  });

  it("moving a column right swaps header, alignment and every row's cell", () => {
    const { target, app, onConfirm } = setup(initial);
    // give columns 0 and 1 distinct alignments so the swap is observable
    (target.querySelectorAll(".te-align-group")[1].querySelector('[title="Align center"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelectorAll(".te-col-move-right")[0] as HTMLButtonElement).click();
    flushSync();
    expect(headerInputs(target).map((i) => i.value)).toEqual(["B", "A", "C"]);
    expect(rowCellValues(target, 0)).toEqual(["r1b", "r1a", "r1c"]);
    target.querySelector(".ui-modal-footer .ui-button-primary")!.dispatchEvent(new Event("click", { bubbles: true }));
    const [, alignments] = onConfirm.mock.calls[0];
    expect(alignments).toEqual(["center", "left", "left"]);
    unmount(app);
    target.remove();
  });

  it("Insert row above/below are disabled until a row is selected", () => {
    const { target, app } = setup(initial);
    expect((target.querySelector(".te-insert-row-above") as HTMLButtonElement).disabled).toBe(true);
    expect((target.querySelector(".te-insert-row-below") as HTMLButtonElement).disabled).toBe(true);
    (dataRows(target)[0].querySelector(".te-row-handle") as HTMLButtonElement).click();
    flushSync();
    expect((target.querySelector(".te-insert-row-above") as HTMLButtonElement).disabled).toBe(false);
    expect((target.querySelector(".te-insert-row-below") as HTMLButtonElement).disabled).toBe(false);
    unmount(app);
    target.remove();
  });

  it("Insert row above adds a blank row above the selected one", () => {
    const { target, app } = setup(initial);
    (dataRows(target)[1].querySelector(".te-row-handle") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".te-insert-row-above") as HTMLButtonElement).click();
    flushSync();
    expect(dataRows(target)).toHaveLength(3);
    expect(rowCellValues(target, 1)).toEqual(["", "", ""]);
    expect(rowCellValues(target, 2)).toEqual(["r2a", "r2b", "r2c"]);
    unmount(app);
    target.remove();
  });

  it("Insert row below adds a blank row below the selected one", () => {
    const { target, app } = setup(initial);
    (dataRows(target)[0].querySelector(".te-row-handle") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".te-insert-row-below") as HTMLButtonElement).click();
    flushSync();
    expect(dataRows(target)).toHaveLength(3);
    expect(rowCellValues(target, 0)).toEqual(["r1a", "r1b", "r1c"]);
    expect(rowCellValues(target, 1)).toEqual(["", "", ""]);
    unmount(app);
    target.remove();
  });

  it("Insert column left/right are disabled until a column is selected", () => {
    const { target, app } = setup(initial);
    expect((target.querySelector(".te-insert-column-left") as HTMLButtonElement).disabled).toBe(true);
    (target.querySelectorAll(".te-col-handle")[0] as HTMLButtonElement).click();
    flushSync();
    expect((target.querySelector(".te-insert-column-left") as HTMLButtonElement).disabled).toBe(false);
    expect((target.querySelector(".te-insert-column-right") as HTMLButtonElement).disabled).toBe(false);
    unmount(app);
    target.remove();
  });

  it("Insert column right adds a blank column to the right of the selected one", () => {
    const { target, app } = setup(initial);
    (target.querySelectorAll(".te-col-handle")[0] as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".te-insert-column-right") as HTMLButtonElement).click();
    flushSync();
    expect(headerInputs(target).map((i) => i.value)).toEqual(["A", "", "B", "C"]);
    expect(rowCellValues(target, 0)).toEqual(["r1a", "", "r1b", "r1c"]);
    unmount(app);
    target.remove();
  });

  it("removing the selected row clears the selection", () => {
    const { target, app } = setup(initial);
    (dataRows(target)[0].querySelector(".te-row-handle") as HTMLButtonElement).click();
    flushSync();
    (dataRows(target)[0].querySelector(".te-row-remove") as HTMLButtonElement).click();
    flushSync();
    expect((target.querySelector(".te-insert-row-above") as HTMLButtonElement).disabled).toBe(true);
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
