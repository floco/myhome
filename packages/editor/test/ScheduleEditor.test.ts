import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ScheduleEditorWrapper from "./fixtures/ScheduleEditorWrapper.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function readState(target: HTMLElement) {
  return JSON.parse(target.querySelector(".state-dump")!.textContent!);
}

function mountWrapper(props: Partial<{ initialFrequencyType: string; initialFrequency: number; initialFrequencyMetadata: Record<string, unknown>; initialPeriodDays: number }> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(ScheduleEditorWrapper, { target, props });
  flushSync();
  return { target, comp };
}

describe("ScheduleEditor", () => {
  it("defaults to the interval category and computes periodDays", () => {
    const { target, comp } = mountWrapper();
    const state = readState(target);
    expect(state.frequencyType).toBe("interval");
    expect(state.periodDays).toBe(30);
    expect(state.valid).toBe(true);
    unmount(comp);
  });

  it("switching to Daily sets frequencyType and a 1-day periodDays", () => {
    const { target, comp } = mountWrapper();
    const select = target.querySelector("#se-category") as HTMLSelectElement;
    select.value = "daily";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    const state = readState(target);
    expect(state.frequencyType).toBe("daily");
    expect(state.periodDays).toBe(1);
    expect(state.valid).toBe(true);
    unmount(comp);
  });

  it("switching to Weekly-on-days is invalid until a day is toggled on", () => {
    const { target, comp } = mountWrapper();
    const select = target.querySelector("#se-category") as HTMLSelectElement;
    select.value = "days_of_the_week";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(readState(target).valid).toBe(false);

    const monButton = Array.from(target.querySelectorAll(".day-toggle")).find((b) => b.textContent === "Mon") as HTMLButtonElement;
    monButton.click();
    flushSync();
    const state = readState(target);
    expect(state.valid).toBe(true);
    expect(state.frequencyMetadata).toEqual({ days: [1] });
    unmount(comp);
  });

  it("switching to Monthly-on-a-day is invalid outside the 1-31 range", () => {
    const { target, comp } = mountWrapper();
    const select = target.querySelector("#se-category") as HTMLSelectElement;
    select.value = "day_of_the_month";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(readState(target).valid).toBe(true); // defaults to day 1

    const dayInput = target.querySelector("#se-dom") as HTMLInputElement;
    dayInput.value = "45";
    dayInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(readState(target).valid).toBe(false);
    unmount(comp);
  });

  it("switching to Yearly is always valid", () => {
    const { target, comp } = mountWrapper();
    const select = target.querySelector("#se-category") as HTMLSelectElement;
    select.value = "yearly";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    const state = readState(target);
    expect(state.frequencyType).toBe("yearly");
    expect(state.periodDays).toBe(365);
    expect(state.valid).toBe(true);
    unmount(comp);
  });

  it("restores an existing adaptive chore's current periodDays on mount, unchanged", () => {
    // Mirrors opening ChoreEditModal for an existing adaptive chore: its
    // periodDays already reflects the backend's learned average (or its
    // original seed), and the picker must show that number, not reset to 30.
    const { target, comp } = mountWrapper({ initialFrequencyType: "adaptive", initialFrequency: 1, initialFrequencyMetadata: {}, initialPeriodDays: 40 });
    const state = readState(target);
    expect(state.frequencyType).toBe("adaptive");
    expect(state.periodDays).toBe(40);
    expect(state.valid).toBe(true);
    unmount(comp);
  });

  it("restores an existing days_of_the_week chore's selected days on mount", () => {
    const { target, comp } = mountWrapper({ initialFrequencyType: "days_of_the_week", initialFrequency: 1, initialFrequencyMetadata: { days: [1, 3] } });
    const active = Array.from(target.querySelectorAll(".day-toggle.active")).map((b) => b.textContent);
    expect(active).toEqual(["Mon", "Wed"]);
    unmount(comp);
  });
});
