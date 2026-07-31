import { describe, it, expect, beforeEach } from "vitest";
import {
  formatDate, formatTime, formatDateTime,
  formatDateWithOptions, formatTimeWithOptions,
} from "../src/lib/dateFormat";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("myhome-locale", "en");
});

describe("formatDateWithOptions", () => {
  const d = new Date(2024, 0, 15); // Jan 15 2024

  it("formats MDY", () => {
    expect(formatDateWithOptions(d, "MDY", "en")).toBe("01/15/2024");
  });

  it("formats DMY", () => {
    expect(formatDateWithOptions(d, "DMY", "en")).toBe("15/01/2024");
  });

  it("formats ISO", () => {
    expect(formatDateWithOptions(d, "ISO", "en")).toBe("2024-01-15");
  });

  it("formats LONG in English", () => {
    expect(formatDateWithOptions(d, "LONG", "en")).toBe("January 15, 2024");
  });

  it("formats LONG in French", () => {
    expect(formatDateWithOptions(d, "LONG", "fr")).toBe("15 janvier 2024");
  });

  it("returns em dash for null/undefined/empty/invalid input", () => {
    expect(formatDateWithOptions(null, "MDY", "en")).toBe("—");
    expect(formatDateWithOptions(undefined, "MDY", "en")).toBe("—");
    expect(formatDateWithOptions("", "MDY", "en")).toBe("—");
    expect(formatDateWithOptions("not-a-date", "MDY", "en")).toBe("—");
  });
});

describe("formatTimeWithOptions", () => {
  const d = new Date(2024, 0, 15, 14, 30);

  it("formats 12h", () => {
    expect(formatTimeWithOptions(d, "12h", "en")).toBe("2:30 PM");
  });

  it("formats 24h", () => {
    expect(formatTimeWithOptions(d, "24h", "en")).toBe("14:30");
  });

  it("returns em dash for invalid input", () => {
    expect(formatTimeWithOptions("nope", "12h", "en")).toBe("—");
  });
});

describe("formatDate / formatTime / formatDateTime (read current settings)", () => {
  it("formatDate uses the current locale's derived date format", () => {
    expect(formatDate("2024-01-15T00:00:00")).toBe("01/15/2024");
  });

  it("formatTime uses the current locale's derived time format", () => {
    expect(formatTime("2024-01-15T14:30:00")).toBe("2:30 PM");
  });

  it("formatDateTime composes date and time with a space", () => {
    expect(formatDateTime("2024-01-15T14:30:00")).toBe("01/15/2024 2:30 PM");
  });

  it("formatDate accepts a Date instance directly", () => {
    expect(formatDate(new Date(2024, 0, 15))).toBe("01/15/2024");
  });

  it("respects an explicit override over the language default", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "ISO", timeFormat: null, weekStart: null }));
    expect(formatDate("2024-01-15T00:00:00")).toBe("2024-01-15");
  });
});
