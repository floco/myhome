import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, createRawSnippet } from "svelte";
import SortableTable from "../src/lib/components/ui/SortableTable.svelte";
import type { Column } from "../src/lib/components/ui/SortableTable.types";

interface Row {
  id: string;
  name: string;
  qty: number;
}

function textSnippet(text: (row: Row) => string) {
  return createRawSnippet((getRow: () => Row) => ({
    render: () => `<span>${text(getRow())}</span>`,
  }));
}

afterEach(() => {
  document.body.innerHTML = "";
});

function baseColumns(): Column<Row>[] {
  return [
    { key: "name", label: "Name", sortValue: (r) => r.name },
    { key: "qty", label: "Qty", sortValue: (r) => r.qty },
    { key: "actions", label: "", sortable: false },
  ];
}

function baseRows(): Row[] {
  return [
    { id: "b", name: "Banana", qty: 3 },
    { id: "a", name: "Apple", qty: 1 },
    { id: "c", name: "Cherry", qty: 2 },
  ];
}

describe("ui/SortableTable", () => {
  it("renders rows in original order when unsorted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Banana", "Apple", "Cherry"]);

    unmount(comp);
  });

  it("sorts ascending then descending then back to unsorted on repeated header clicks", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const nameHeaderBtn = target.querySelector("thead th:first-child button")!;
    (nameHeaderBtn as HTMLButtonElement).click();
    flushSync();
    let names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Apple", "Banana", "Cherry"]);

    (nameHeaderBtn as HTMLButtonElement).click();
    flushSync();
    names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Cherry", "Banana", "Apple"]);

    (nameHeaderBtn as HTMLButtonElement).click();
    flushSync();
    names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Banana", "Apple", "Cherry"]);

    unmount(comp);
  });

  it("sets aria-sort on the active column header", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const nameTh = target.querySelector("thead th:first-child")!;
    expect(nameTh.getAttribute("aria-sort")).toBe("none");
    (target.querySelector("thead th:first-child button") as HTMLButtonElement).click();
    flushSync();
    expect(nameTh.getAttribute("aria-sort")).toBe("ascending");

    unmount(comp);
  });

  it("does not render a sort button for non-sortable columns", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    const actionsTh = target.querySelector("thead th:last-child")!;
    expect(actionsTh.querySelector("button")).toBeNull();
    expect(actionsTh.hasAttribute("aria-sort")).toBe(false);

    unmount(comp);
  });

  it("renders custom cell snippets", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const columns: Column<Row>[] = [
      { key: "name", label: "Name", sortValue: (r) => r.name, cell: textSnippet((r) => `★ ${r.name}`) },
    ];
    const comp = mount(SortableTable, {
      target,
      props: { columns, rows: baseRows(), rowKey: (r: Row) => r.id },
    });
    flushSync();

    expect(target.querySelector("tbody tr td span")?.textContent).toBe("★ Banana");

    unmount(comp);
  });

  it("fires rowClick when a row is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const rowClick = vi.fn();
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id, rowClick },
    });
    flushSync();

    (target.querySelector("tbody tr") as HTMLTableRowElement).click();
    expect(rowClick).toHaveBeenCalledOnce();
    expect(rowClick).toHaveBeenCalledWith(baseRows()[0]);

    unmount(comp);
  });

  it("renders emptyMessage when rows is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: [], rowKey: (r: Row) => r.id, emptyMessage: "Nothing here" },
    });
    flushSync();

    const emptyCell = target.querySelector("tbody tr td")!;
    expect(emptyCell.textContent).toBe("Nothing here");
    expect(emptyCell.getAttribute("colspan")).toBe("3");

    unmount(comp);
  });

  it("applies defaultSort on mount", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(SortableTable, {
      target,
      props: {
        columns: baseColumns(),
        rows: baseRows(),
        rowKey: (r: Row) => r.id,
        defaultSort: { key: "qty", direction: "asc" },
      },
    });
    flushSync();

    const names = [...target.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    expect(names).toEqual(["Apple", "Cherry", "Banana"]); // qty 1, 2, 3

    unmount(comp);
  });

  it("renders extraRow as the last row in tbody when provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const extraRow = createRawSnippet(() => ({
      render: () => `<td colspan="3" class="new-row-marker">new row</td>`,
    }));
    const comp = mount(SortableTable, {
      target,
      props: { columns: baseColumns(), rows: baseRows(), rowKey: (r: Row) => r.id, extraRow },
    });
    flushSync();

    const allRows = [...target.querySelectorAll("tbody tr")];
    expect(allRows).toHaveLength(4); // 3 data rows + 1 extra row
    expect(allRows[3].querySelector(".new-row-marker")).not.toBeNull();

    unmount(comp);
  });

  it("renders an expanded detail row only for rows where isRowExpanded returns true", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const expandedRow = createRawSnippet((getRow: () => Row) => ({
      render: () => `<div class="detail">detail for ${getRow().id}</div>`,
    }));
    const comp = mount(SortableTable, {
      target,
      props: {
        columns: baseColumns(),
        rows: baseRows(),
        rowKey: (r: Row) => r.id,
        isRowExpanded: (r: Row) => r.id === "a",
        expandedRow,
      },
    });
    flushSync();

    const details = target.querySelectorAll(".detail");
    expect(details).toHaveLength(1);
    expect(details[0].textContent).toBe("detail for a");

    unmount(comp);
  });
});
