import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import HorizontalBarChart from "../src/lib/components/HorizontalBarChart.svelte";

const segments = [
  { id: "ok", label: "OK", emoji: "🟢", color: "#4caf50", valueLabel: "8", pct: 80 },
  { id: "low", label: "Low", emoji: "🟠", color: "#ff9800", valueLabel: "2", pct: 20 },
];

describe("HorizontalBarChart", () => {
  it("renders one stacked segment per input segment, sized by pct", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const segs = Array.from(target.querySelectorAll(".stacked-segment")) as HTMLElement[];
    expect(segs).toHaveLength(2);
    expect(segs[0].style.width).toBe("80%");
    expect(segs[1].style.width).toBe("20%");
    unmount(comp);
    target.remove();
  });

  it("shows the value inside a segment large enough to hold it", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const segs = Array.from(target.querySelectorAll(".stacked-segment")) as HTMLElement[];
    expect(segs[0].textContent).toContain("8");
    expect(segs[1].textContent).toContain("2");
    unmount(comp);
    target.remove();
  });

  it("hides the inside value for a segment too narrow to hold it", () => {
    const skewed = [
      { id: "ok", label: "OK", emoji: "🟢", color: "#4caf50", valueLabel: "97", pct: 97 },
      { id: "low", label: "Low", emoji: "🟠", color: "#ff9800", valueLabel: "3", pct: 3 },
    ];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments: skewed } });
    flushSync();
    const segs = Array.from(target.querySelectorAll(".stacked-segment")) as HTMLElement[];
    expect(segs[0].textContent).toContain("97");
    expect(segs[1].textContent).toBe("");
    unmount(comp);
    target.remove();
  });

  it("renders a legend row per segment with label and value, no color swatch", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const items = target.querySelectorAll(".legend-item");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain("OK");
    expect(items[0].textContent).toContain("8");
    expect(target.querySelectorAll(".legend-swatch")).toHaveLength(0);
    unmount(comp);
    target.remove();
  });

  it("preserves input order rather than sorting by value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments: [segments[1], segments[0]] } });
    flushSync();
    const labels = Array.from(target.querySelectorAll(".legend-label")).map((el) => el.textContent);
    expect(labels).toEqual(["🟠 Low", "🟢 OK"]);
    unmount(comp);
    target.remove();
  });

  it("renders no segments or legend items for an empty segment list", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments: [] } });
    flushSync();
    expect(target.querySelectorAll(".stacked-segment")).toHaveLength(0);
    expect(target.querySelectorAll(".legend-item")).toHaveLength(0);
    unmount(comp);
    target.remove();
  });

  it("includes the value and percent in each segment's title tooltip", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HorizontalBarChart, { target, props: { segments } });
    flushSync();
    const seg = target.querySelector(".stacked-segment") as HTMLElement;
    expect(seg.title).toBe("OK: 8 (80%)");
    unmount(comp);
    target.remove();
  });
});
