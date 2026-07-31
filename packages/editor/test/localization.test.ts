import { describe, it, expect, beforeEach } from "vitest";
import {
  getDateFormat, setDateFormat,
  getTimeFormat, setTimeFormat,
  getWeekStart, setWeekStart,
} from "../src/lib/localization";

beforeEach(() => {
  localStorage.clear();
});

describe("localization defaults (derived from language)", () => {
  it("defaults to MDY/12h/Sunday for English", () => {
    localStorage.setItem("myhome-locale", "en");
    expect(getDateFormat()).toBe("MDY");
    expect(getTimeFormat()).toBe("12h");
    expect(getWeekStart()).toBe(0);
  });

  it("defaults to DMY/24h/Monday for French", () => {
    localStorage.setItem("myhome-locale", "fr");
    expect(getDateFormat()).toBe("DMY");
    expect(getTimeFormat()).toBe("24h");
    expect(getWeekStart()).toBe(1);
  });
});

describe("localization explicit overrides", () => {
  it("setDateFormat persists an override that getDateFormat returns", () => {
    localStorage.setItem("myhome-locale", "en");
    setDateFormat("ISO");
    expect(getDateFormat()).toBe("ISO");
  });

  it("setTimeFormat persists an override that getTimeFormat returns", () => {
    localStorage.setItem("myhome-locale", "en");
    setTimeFormat("24h");
    expect(getTimeFormat()).toBe("24h");
  });

  it("setWeekStart persists an override that getWeekStart returns", () => {
    localStorage.setItem("myhome-locale", "en");
    setWeekStart(6);
    expect(getWeekStart()).toBe(6);
  });

  it("an explicit override survives a later language change", () => {
    localStorage.setItem("myhome-locale", "en");
    setDateFormat("DMY");
    localStorage.setItem("myhome-locale", "fr");
    expect(getDateFormat()).toBe("DMY");
    // timeFormat was never overridden, so it still follows the new language
    expect(getTimeFormat()).toBe("24h");
  });

  it("setting one field does not clobber the others", () => {
    localStorage.setItem("myhome-locale", "en");
    setDateFormat("ISO");
    setWeekStart(1);
    expect(getDateFormat()).toBe("ISO");
    expect(getWeekStart()).toBe(1);
    expect(getTimeFormat()).toBe("12h");
  });
});
