import { describe, it, expect } from "vitest";
import { findTableAtCursor, serializeTable } from "../src/lib/components/ui/markdownTable";

describe("serializeTable", () => {
  it("serializes header, alignment row and data rows as GFM pipe table", () => {
    const md = serializeTable(["Name", "Qty"], ["left", "left"], [["Apples", "3"], ["Pears", "5"]]);
    expect(md).toBe(
      "| Name | Qty |\n| :--- | :--- |\n| Apples | 3 |\n| Pears | 5 |",
    );
  });

  it("emits :---: for center and ---: for right alignment", () => {
    const md = serializeTable(["A", "B", "C"], ["left", "center", "right"], [["1", "2", "3"]]);
    expect(md.split("\n")[1]).toBe("| :--- | :---: | ---: |");
  });

  it("escapes literal pipe characters in cell content", () => {
    const md = serializeTable(["A"], ["left"], [["a|b"]]);
    expect(md).toContain("a\\|b");
  });
});

describe("findTableAtCursor", () => {
  const doc = [
    "Some intro text.",
    "",
    "| Name | Qty |",
    "| :--- | ---: |",
    "| Apples | 3 |",
    "| Pears | 5 |",
    "",
    "Trailing paragraph.",
  ].join("\n");

  it("returns null when cursor is outside any table", () => {
    const cursor = doc.indexOf("Some intro");
    expect(findTableAtCursor(doc, cursor)).toBeNull();
  });

  it("returns null on the trailing paragraph after the table", () => {
    const cursor = doc.indexOf("Trailing paragraph");
    expect(findTableAtCursor(doc, cursor)).toBeNull();
  });

  it("parses header cells, alignments and data rows when cursor is on the header row", () => {
    const cursor = doc.indexOf("| Name");
    const table = findTableAtCursor(doc, cursor);
    expect(table).not.toBeNull();
    expect(table!.headerCells).toEqual(["Name", "Qty"]);
    expect(table!.alignments).toEqual(["left", "right"]);
    expect(table!.rows).toEqual([["Apples", "3"], ["Pears", "5"]]);
  });

  it("parses the same table when cursor is inside a data row", () => {
    const cursor = doc.indexOf("Pears");
    const table = findTableAtCursor(doc, cursor);
    expect(table!.rows).toEqual([["Apples", "3"], ["Pears", "5"]]);
  });

  it("reports startIndex/endIndex spanning exactly the table block", () => {
    const cursor = doc.indexOf("Apples");
    const table = findTableAtCursor(doc, cursor)!;
    expect(doc.slice(table.startIndex, table.endIndex)).toBe(
      "| Name | Qty |\n| :--- | ---: |\n| Apples | 3 |\n| Pears | 5 |",
    );
  });

  it("unescapes escaped pipe characters in parsed cells", () => {
    const withEscapedPipe = "| A |\n| :--- |\n| a\\|b |";
    const table = findTableAtCursor(withEscapedPipe, 0)!;
    expect(table.rows).toEqual([["a|b"]]);
  });

  it("round-trips through serializeTable back to the same source slice", () => {
    const cursor = doc.indexOf("Apples");
    const table = findTableAtCursor(doc, cursor)!;
    const rebuilt = serializeTable(table.headerCells, table.alignments, table.rows);
    expect(rebuilt).toBe(doc.slice(table.startIndex, table.endIndex));
  });
});
