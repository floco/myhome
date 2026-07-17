import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import HorizontalBarChart from "../src/lib/components/HorizontalBarChart.svelte";

const segments = [
  { id: "ok", label: "OK", emoji: "🟢", color: "#4caf50", valueLabel: "8", pct: 80 },
  { id: "low", label: "Low", emoji: "🟠", color: "#ff9800", valueLabel: "2", pct: 20 },
];

describe("HorizontalBarChart", () => {
  it("renders one row per segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    expect(target.querySelectorAll(".hbar-row")).toHaveLength(2);
    unmount(comp);
    target.remove();
  });

  it("scales bar width relative to the largest segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const fills = Array.from(target.querySelectorAll(".hbar-fill")) as HTMLElement[];
    expect(fills[0].style.width).toBe("100%");
    expect(fills[1].style.width).toBe("25%");
    unmount(comp);
    target.remove();
  });

  it("preserves input order rather than sorting by value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments: [segments[1], segments[0]] } });
    flushSync();
    const labels = Array.from(target.querySelectorAll(".hbar-label")).map((el) => el.textContent);
    expect(labels).toEqual(["🟠 Low", "🟢 OK"]);
    unmount(comp);
    target.remove();
  });

  it("renders no rows for an empty segment list", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments: [] } });
    flushSync();
    expect(target.querySelectorAll(".hbar-row")).toHaveLength(0);
    unmount(comp);
    target.remove();
  });

  it("includes the value and percent in the row's title tooltip", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const row = target.querySelector(".hbar-row") as HTMLElement;
    expect(row.title).toBe("OK: 8 (80%)");
    unmount(comp);
    target.remove();
  });
});
