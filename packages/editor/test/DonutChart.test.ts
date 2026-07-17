import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import DonutChart from "../src/lib/components/DonutChart.svelte";

const segments = [
  { id: "a", label: "Fuel", emoji: "⛽", color: "#e76f51", valueLabel: "300 €", pct: 60 },
  { id: "b", label: "Tax", emoji: "🏛️", color: "#2a9d8f", valueLabel: "200 €", pct: 40 },
];

describe("DonutChart", () => {
  it("renders one slice path per segment", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €" },
    });

    expect(target.querySelectorAll("svg path")).toHaveLength(2);

    unmount(comp);
    target.remove();
  });

  it("renders the center label and value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €" },
    });

    expect(target.textContent).toContain("Total");
    expect(target.textContent).toContain("500 €");

    unmount(comp);
    target.remove();
  });

  it("does not render connector-line labels by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €" },
    });

    expect(target.textContent).not.toContain("Fuel");

    unmount(comp);
    target.remove();
  });

  it("renders connector-line labels when showLabels is true", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €", showLabels: true },
    });

    expect(target.textContent).toContain("Fuel");
    expect(target.textContent).toContain("Tax");

    unmount(comp);
    target.remove();
  });

  it("shows icon + percent inside large slices when insideLabels is set, without the category name", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €", showLabels: true, insideLabels: true },
    });

    // Both slices (60%/40%) render icon + percent, nothing else.
    expect(target.textContent).toContain("60%");
    expect(target.textContent).toContain("40%");
    expect(target.textContent).not.toContain("Fuel");
    expect(target.textContent).not.toContain("Tax");
    expect(target.textContent).not.toContain("300 €");
    // No connector lines -- everything renders inside.
    expect(target.querySelectorAll("svg line")).toHaveLength(0);

    unmount(comp);
    target.remove();
  });

  it("keeps every slice's label inside regardless of size, shrinking text to fit narrower slices", () => {
    const skewed = [
      { id: "a", label: "Mortgage", emoji: "🏠", color: "#2a78d6", valueLabel: "10,000 €", pct: 95 },
      { id: "b", label: "Misc", emoji: "❔", color: "#e34948", valueLabel: "500 €", pct: 5 },
    ];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(DonutChart, {
      target,
      props: { segments: skewed, centerLabel: "Total", centerValue: "10,500 €", showLabels: true, insideLabels: true },
    });

    expect(target.textContent).toContain("95%");
    expect(target.textContent).toContain("5%");
    expect(target.textContent).not.toContain("Mortgage");
    expect(target.textContent).not.toContain("Misc");
    // No connector lines -- even the 5% slice's label stays inside.
    expect(target.querySelectorAll("svg line")).toHaveLength(0);

    const texts = Array.from(target.querySelectorAll("svg text")).filter((t) => t.textContent?.includes("%"));
    expect(texts).toHaveLength(2);
    const bigFont = Number(texts.find((t) => t.textContent === "🏠 95%")!.getAttribute("font-size"));
    const smallFont = Number(texts.find((t) => t.textContent === "❔ 5%")!.getAttribute("font-size"));
    expect(smallFont).toBeLessThan(bigFont);

    unmount(comp);
    target.remove();
  });

  it("calls onsliceclick with the segment id when a slice is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onsliceclick = vi.fn();
    const comp = mount(DonutChart, {
      target,
      props: { segments, centerLabel: "Total", centerValue: "500 €", onsliceclick },
    });

    (target.querySelectorAll("svg path")[0] as SVGPathElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    flushSync();

    expect(onsliceclick).toHaveBeenCalledWith("a");

    unmount(comp);
    target.remove();
  });
});
