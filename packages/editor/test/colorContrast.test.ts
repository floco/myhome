import { describe, it, expect } from "vitest";
import { textColorForFill } from "../src/lib/colorContrast";

describe("textColorForFill", () => {
  it("picks dark text on a white fill", () => {
    expect(textColorForFill("#ffffff")).toBe("#111111");
  });

  it("picks light text on a black fill", () => {
    expect(textColorForFill("#000000")).toBe("#ffffff");
  });

  it("picks light text on a mid-dark blue fill", () => {
    expect(textColorForFill("#2a78d6")).toBe("#ffffff");
  });

  it("picks dark text on a light yellow fill", () => {
    expect(textColorForFill("#eda100")).toBe("#111111");
  });

  it("falls back to dark text for an unparseable value", () => {
    expect(textColorForFill("not-a-color")).toBe("#111111");
    expect(textColorForFill("var(--chart-series-1)")).toBe("#111111");
  });
});
