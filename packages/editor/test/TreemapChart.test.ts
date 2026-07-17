import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import TreemapChart from "../src/lib/components/TreemapChart.svelte";

const segments = [
  { id: "a", label: "Mortgage", emoji: "🏠", color: "#2a78d6", valueLabel: "10,000 €", pct: 70 },
  { id: "b", label: "Utilities", emoji: "💡", color: "#eda100", valueLabel: "3,000 €", pct: 21 },
  { id: "c", label: "Tax", emoji: "🏛️", color: "#e34948", valueLabel: "1,300 €", pct: 9 },
];

describe("TreemapChart", () => {
  it("renders one rect per segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(TreemapChart, { target, props: { segments } });
    flushSync();
    expect(target.querySelectorAll("svg rect")).toHaveLength(3);
    unmount(comp);
    target.remove();
  });

  it("sizes the largest segment's rect area larger than the smallest", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(TreemapChart, { target, props: { segments } });
    flushSync();
    const areaOf = (r: Element) => Number(r.getAttribute("width")) * Number(r.getAttribute("height"));
    const areas = Array.from(target.querySelectorAll("svg rect")).map(areaOf);
    expect(Math.max(...areas)).toBeGreaterThan(Math.min(...areas));
    unmount(comp);
    target.remove();
  });

  it("shows emoji, label, and value text for a single full-size segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const single = [{ id: "a", label: "Mortgage", emoji: "🏠", color: "#2a78d6", valueLabel: "10,000 €", pct: 100 }];
    const comp = mount(TreemapChart, { target, props: { segments: single } });
    flushSync();
    const text = target.querySelector("svg")!.textContent ?? "";
    expect(text).toContain("Mortgage");
    expect(text).toContain("10,000 €");
    unmount(comp);
    target.remove();
  });

  it("calls onsliceclick with the segment id when a cell is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onsliceclick = vi.fn();
    const comp = mount(TreemapChart, { target, props: { segments, onsliceclick } });
    flushSync();
    (target.querySelector("svg g") as SVGGElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(onsliceclick).toHaveBeenCalledOnce();
    unmount(comp);
    target.remove();
  });

  it("filters out zero-pct segments", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const withZero = [...segments, { id: "z", label: "Zero", emoji: "0", color: "#000000", valueLabel: "0 €", pct: 0 }];
    const comp = mount(TreemapChart, { target, props: { segments: withZero } });
    flushSync();
    expect(target.querySelectorAll("svg rect")).toHaveLength(3);
    unmount(comp);
    target.remove();
  });
});
