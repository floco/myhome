import { describe, it, expect } from "vitest";
import { COUNTRY_FLAGS, flagEmoji } from "../src/lib/countryFlags";

describe("flagEmoji", () => {
  it("produces the correct regional-indicator pair for known codes", () => {
    expect(flagEmoji("FR")).toBe("🇫🇷");
    expect(flagEmoji("US")).toBe("🇺🇸");
    expect(flagEmoji("jp")).toBe("🇯🇵");
  });
});

describe("COUNTRY_FLAGS", () => {
  it("has no duplicate codes", () => {
    const codes = COUNTRY_FLAGS.map((c) => c.code);
    expect(new Set(codes).size).toBe(codes.length);
  });

  it("every entry has a non-empty name and a computed flag", () => {
    for (const c of COUNTRY_FLAGS) {
      expect(c.name.length).toBeGreaterThan(0);
      expect(c.flag).toBe(flagEmoji(c.code));
    }
  });

  it("is sorted by name", () => {
    const names = COUNTRY_FLAGS.map((c) => c.name);
    const sorted = [...names].sort((a, b) => a.localeCompare(b));
    expect(names).toEqual(sorted);
  });
});
