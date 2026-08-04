import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import DatePicker from "../src/lib/components/DatePicker.svelte";

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
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const headers = [...target.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Sun");
    unmount(app);
  });

  it("starts the grid on Monday when the week-start preference is Monday", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const headers = [...target.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Mon");
    unmount(app);
  });

  it("shifts the leading blank cells to match a Monday-first grid", () => {
    // January 2024: the 1st is a Monday. Sunday-first grid needs 1 leading blank
    // (Jan 1 falls in column index 1); Monday-first grid needs 0 leading blanks.
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: { value: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const cells = [...target.querySelectorAll(".dp-cell")];
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
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();

    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day20 = cells.find((c) => c.textContent === "20")!;
    expect(day20.disabled).toBe(true);

    day20.click();
    flushSync();

    expect(target.querySelector(".dp-text")!.textContent).toContain("10");
    unmount(app);
  });

  it("still allows selecting a day at or before max", () => {
    const app = mount(DatePicker, { target, props: { value: "2024-01-10", max: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();

    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const day15 = cells.find((c) => c.textContent === "15")!;
    expect(day15.disabled).toBe(false);

    day15.click();
    flushSync();

    expect(target.querySelector(".dp-text")!.textContent).toContain("15");
    unmount(app);
  });
});
