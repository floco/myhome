import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import DatePicker from "../src/lib/components/ui/DatePicker.svelte";

describe("DatePicker week start", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("defaults to a Sunday-first grid", () => {
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    (document.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    const headers = [...document.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Sun");
    unmount(app);
  });

  it("starts the grid on Monday when the week-start preference is Monday", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    (document.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    const headers = [...document.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Mon");
    unmount(app);
  });

  it("shifts the leading blank cells to match a Monday-first grid", () => {
    // January 2024: the 1st is a Monday. Sunday-first grid needs 1 leading blank
    // (Jan 1 falls in column index 1); Monday-first grid needs 0 leading blanks.
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: { value: "2024-01-15" } });
    flushSync();
    (document.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    const cells = [...document.querySelectorAll(".dp-cell")];
    expect(cells[0].classList.contains("dp-empty")).toBe(false);
    expect(cells[0].textContent).toBe("1");
    unmount(app);
  });
});

describe("DatePicker max", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("disables and ignores clicks on days after max", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();
    (document.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();

    const cells = [...document.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day20 = cells.find((c) => c.textContent === "20")!;
    expect(day20.disabled).toBe(true);

    day20.click();
    flushSync();

    expect((document.querySelector(".dp-input") as HTMLInputElement).value).toContain("10");
    unmount(app);
  });

  it("still allows selecting a day at or before max", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();
    (document.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();

    const cells = [...document.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day15 = cells.find((c) => c.textContent === "15")!;
    expect(day15.disabled).toBe(false);

    day15.click();
    flushSync();

    expect((document.querySelector(".dp-input") as HTMLInputElement).value).toContain("15");
    unmount(app);
  });
});

describe("DatePicker date format", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("displays DMY when the Settings date format is DMY", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "DMY", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((document.querySelector(".dp-input") as HTMLInputElement).value).toBe("05/07/2026");
    unmount(app);
  });

  it("displays MDY when the Settings date format is MDY", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "MDY", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((document.querySelector(".dp-input") as HTMLInputElement).value).toBe("07/05/2026");
    unmount(app);
  });

  it("displays ISO when the Settings date format is ISO", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "ISO", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((document.querySelector(".dp-input") as HTMLInputElement).value).toBe("2026-07-05");
    unmount(app);
  });

  it("falls back to the en-locale default (MDY) when no override is set", () => {
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((document.querySelector(".dp-input") as HTMLInputElement).value).toBe("07/05/2026");
    unmount(app);
  });

  it("displays LONG when the Settings date format is explicitly LONG", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "LONG", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2026-07-05" } });
    flushSync();
    expect((document.querySelector(".dp-input") as HTMLInputElement).value).toBe("05 July 2026");
    unmount(app);
  });
});

describe("DatePicker compact", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("applies the compact class when the compact prop is set", () => {
    const app = mount(DatePicker, { target, props: { compact: true } });
    flushSync();
    expect(document.querySelector(".dp-field")!.classList.contains("compact")).toBe(true);
    unmount(app);
  });

  it("does not apply the compact class by default", () => {
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    expect(document.querySelector(".dp-field")!.classList.contains("compact")).toBe(false);
    unmount(app);
  });
});

describe("DatePicker manual entry", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("commits a valid typed date on blur", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "03/05/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("03/05/2024");
    unmount(app);
  });

  it("commits a valid typed date on Enter", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "12/25/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();

    expect(input.value).toBe("12/25/2024");
    unmount(app);
  });

  it("reverts to the last valid value when the typed text is unparseable", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "not a date";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("01/10/2024");
    unmount(app);
  });

  it("reverts without committing on Escape", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "12/25/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    flushSync();

    expect(input.value).toBe("01/10/2024");
    unmount(app);
  });

  it("rejects a typed date beyond max and reverts", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "01/20/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("01/10/2024");
    unmount(app);
  });

  it("parses a typed DMY date when the Settings date format is DMY", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "DMY", timeFormat: null, weekStart: null }));
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    input.value = "25/12/2024";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.blur();
    flushSync();

    expect(input.value).toBe("25/12/2024");
    unmount(app);
  });

  it("stops the Enter keydown from propagating, so an ancestor form can't treat it as a submit", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    const event = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    const stopSpy = vi.spyOn(event, "stopPropagation");
    input.dispatchEvent(event);
    flushSync();

    expect(stopSpy).toHaveBeenCalled();
    unmount(app);
  });

  it("stops the Escape keydown from propagating, so an ancestor modal can't treat it as a close", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10" } });
    flushSync();

    const input = document.querySelector(".dp-input") as HTMLInputElement;
    input.focus();
    const event = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
    const stopSpy = vi.spyOn(event, "stopPropagation");
    input.dispatchEvent(event);
    flushSync();

    expect(stopSpy).toHaveBeenCalled();
    unmount(app);
  });
});

describe("DatePicker year grid", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  function openCalendar(): void {
    (document.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
  }

  it("switches to a 12-year grid when the month/year label is clicked", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();

    (document.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();

    const years = [...document.querySelectorAll(".dp-year-cell")].map((c) => c.textContent);
    expect(years).toEqual(["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027"]);
    const selected = document.querySelector(".dp-year-cell.dp-selected");
    expect(selected?.textContent).toBe("2024");
    unmount(app);
  });

  it("pages the year grid forward and backward by 12 years", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();
    (document.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();

    const [prevBtn, nextBtn] = [...document.querySelectorAll(".dp-nav")] as HTMLButtonElement[];
    nextBtn.click();
    flushSync();
    let years = [...document.querySelectorAll(".dp-year-cell")].map((c) => c.textContent);
    expect(years[0]).toBe("2028");

    prevBtn.click();
    flushSync();
    years = [...document.querySelectorAll(".dp-year-cell")].map((c) => c.textContent);
    expect(years[0]).toBe("2016");
    unmount(app);
  });

  it("selecting a year returns to the day grid for that year, keeping the month", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();
    (document.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();

    const yearCell = [...document.querySelectorAll(".dp-year-cell")].find((c) => c.textContent === "2018") as HTMLButtonElement;
    yearCell.click();
    flushSync();

    expect(document.querySelector(".dp-grid")).not.toBeNull();
    expect(document.querySelector(".dp-year-grid")).toBeNull();
    expect(document.querySelector(".dp-month-label")!.textContent).toBe("June 2018");
    unmount(app);
  });

  it("reopening the calendar always starts on the day view", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-06-15" } });
    flushSync();
    openCalendar();
    (document.querySelector(".dp-month-label") as HTMLElement).click();
    flushSync();
    expect(document.querySelector(".dp-year-grid")).not.toBeNull();

    // close (click icon again) and reopen
    (document.querySelector(".dp-icon-btn") as HTMLElement).click();
    flushSync();
    openCalendar();

    expect(document.querySelector(".dp-grid")).not.toBeNull();
    expect(document.querySelector(".dp-year-grid")).toBeNull();
    unmount(app);
  });
});
