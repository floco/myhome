import { describe, it, expect } from "vitest";
import { createSortState, compareValues } from "../src/lib/utils/sortState.svelte";

describe("compareValues", () => {
  it("compares numbers numerically", () => {
    expect(compareValues(2, 10)).toBeLessThan(0);
  });

  it("compares strings case-insensitively", () => {
    expect(compareValues("banana", "Apple")).toBeGreaterThan(0);
  });

  it("compares dates by timestamp", () => {
    const a = new Date("2026-01-01");
    const b = new Date("2026-06-01");
    expect(compareValues(a, b)).toBeLessThan(0);
  });

  it("sorts null and undefined to the end regardless of comparand", () => {
    expect(compareValues(null, 5)).toBeGreaterThan(0);
    expect(compareValues(5, undefined)).toBeLessThan(0);
    expect(compareValues(null, undefined)).toBe(0);
  });
});

describe("createSortState", () => {
  it("starts with no active sort", () => {
    const s = createSortState();
    expect(s.current).toBeNull();
    expect(s.directionFor("name")).toBeNull();
  });

  it("cycles a column asc -> desc -> unsorted", () => {
    const s = createSortState();
    s.toggle("name");
    expect(s.current).toEqual({ key: "name", direction: "asc" });
    s.toggle("name");
    expect(s.current).toEqual({ key: "name", direction: "desc" });
    s.toggle("name");
    expect(s.current).toBeNull();
  });

  it("switching to a different column resets to ascending", () => {
    const s = createSortState();
    s.toggle("name");
    s.toggle("name"); // now desc on "name"
    s.toggle("date");
    expect(s.current).toEqual({ key: "date", direction: "asc" });
  });

  it("accepts an initial sort state", () => {
    const s = createSortState({ key: "date", direction: "desc" });
    expect(s.current).toEqual({ key: "date", direction: "desc" });
    expect(s.directionFor("date")).toBe("desc");
  });

  it("sortRows returns the original array order when unsorted", () => {
    const s = createSortState();
    const rows = [{ n: 3 }, { n: 1 }, { n: 2 }];
    expect(s.sortRows(rows, (r) => r.n)).toEqual(rows);
  });

  it("sortRows sorts ascending then descending without mutating the input", () => {
    const s = createSortState();
    const rows = [{ n: 3 }, { n: 1 }, { n: 2 }];
    s.toggle("n");
    const asc = s.sortRows(rows, (r) => r.n);
    expect(asc.map((r) => r.n)).toEqual([1, 2, 3]);
    expect(rows.map((r) => r.n)).toEqual([3, 1, 2]); // original untouched

    s.toggle("n");
    const desc = s.sortRows(rows, (r) => r.n);
    expect(desc.map((r) => r.n)).toEqual([3, 2, 1]);
  });

  it("sortRows keeps null/undefined values last in both directions", () => {
    const s = createSortState();
    const rows = [{ n: 2 }, { n: null as number | null }, { n: 1 }];
    s.toggle("n");
    expect(s.sortRows(rows, (r) => r.n).map((r) => r.n)).toEqual([1, 2, null]);
    s.toggle("n");
    expect(s.sortRows(rows, (r) => r.n).map((r) => r.n)).toEqual([2, 1, null]);
  });
});
