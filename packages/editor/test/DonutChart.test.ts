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
