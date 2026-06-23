import { describe, it, expect, beforeEach } from "vitest";
import { getStoredTheme, applyTheme, setTheme, initTheme, toggleTheme } from "../src/lib/theme";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("theme", () => {
  it("defaults to light when nothing is stored", () => {
    expect(getStoredTheme()).toBe("light");
  });

  it("returns the stored theme when present", () => {
    localStorage.setItem("myhome-theme", "dark");
    expect(getStoredTheme()).toBe("dark");
  });

  it("applyTheme sets the data-theme attribute on the html element", () => {
    applyTheme("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("setTheme persists to localStorage and applies the attribute", () => {
    setTheme("dark");
    expect(localStorage.getItem("myhome-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("initTheme applies and returns the stored theme", () => {
    localStorage.setItem("myhome-theme", "dark");
    expect(initTheme()).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("initTheme defaults to light and applies it when nothing stored", () => {
    expect(initTheme()).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggleTheme flips light to dark and persists it", () => {
    expect(toggleTheme("light")).toBe("dark");
    expect(localStorage.getItem("myhome-theme")).toBe("dark");
  });

  it("toggleTheme flips dark to light and persists it", () => {
    expect(toggleTheme("dark")).toBe("light");
    expect(localStorage.getItem("myhome-theme")).toBe("light");
  });
});
