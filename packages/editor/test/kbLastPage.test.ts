import { describe, it, expect, beforeEach } from "vitest";
import { getStoredLastPageId, setStoredLastPageId, clearStoredLastPageId } from "../src/lib/kbLastPage";

beforeEach(() => localStorage.clear());

describe("kbLastPage", () => {
  it("returns null when nothing is stored for a home", () => {
    expect(getStoredLastPageId("home-1")).toBeNull();
  });

  it("stores and retrieves a page id scoped to a home", () => {
    setStoredLastPageId("home-1", "page-a");
    expect(getStoredLastPageId("home-1")).toBe("page-a");
    expect(getStoredLastPageId("home-2")).toBeNull();
  });

  it("overwrites the previous value for the same home", () => {
    setStoredLastPageId("home-1", "page-a");
    setStoredLastPageId("home-1", "page-b");
    expect(getStoredLastPageId("home-1")).toBe("page-b");
  });

  it("clears the stored value for a home without affecting other homes", () => {
    setStoredLastPageId("home-1", "page-a");
    setStoredLastPageId("home-2", "page-c");
    clearStoredLastPageId("home-1");
    expect(getStoredLastPageId("home-1")).toBeNull();
    expect(getStoredLastPageId("home-2")).toBe("page-c");
  });
});
