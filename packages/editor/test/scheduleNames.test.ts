import { describe, it, expect } from "vitest";
import { toWeekdayNum, toMonthNum } from "../src/lib/scheduleNames";

describe("toWeekdayNum", () => {
  it("passes through an int unchanged", () => {
    expect(toWeekdayNum(3)).toBe(3);
  });
  it("converts a full Donetick day name, case-insensitively", () => {
    expect(toWeekdayNum("Tuesday")).toBe(2);
    expect(toWeekdayNum("SUNDAY")).toBe(7);
  });
  it("converts an abbreviated day name", () => {
    expect(toWeekdayNum("mon")).toBe(1);
  });
  it("returns null for unrecognized input", () => {
    expect(toWeekdayNum("not-a-day")).toBeNull();
  });
});

describe("toMonthNum", () => {
  it("passes through an int unchanged", () => {
    expect(toMonthNum(9)).toBe(9);
  });
  it("converts a full Donetick month name, case-insensitively", () => {
    expect(toMonthNum("March")).toBe(3);
    expect(toMonthNum("DECEMBER")).toBe(12);
  });
  it("returns null for unrecognized input", () => {
    expect(toMonthNum("not-a-month")).toBeNull();
  });
});
