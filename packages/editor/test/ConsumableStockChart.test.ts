import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ConsumableStockChart from "../src/lib/components/ConsumableStockChart.svelte";
import type { ConsumableTransaction } from "../src/lib/consumableStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeTx(overrides: Partial<ConsumableTransaction> = {}): ConsumableTransaction {
  return {
    id: "t1", consumableId: "c1", delta: 100, quantityAfter: 100,
    note: "", timestamp: "2026-01-01T00:00:00Z", costEntryId: null,
    ...overrides,
  };
}

describe("ConsumableStockChart", () => {
  it("shows an empty state with fewer than 2 transactions", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableStockChart, {
      target,
      props: { transactions: [makeTx()], unit: "L", minQuantity: 50 },
    });
    flushSync();
    expect(target.querySelector(".chart-empty")).not.toBeNull();
    expect(target.querySelector("svg")).toBeNull();
    unmount(comp);
  });

  it("shows an empty state with zero transactions", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableStockChart, {
      target,
      props: { transactions: [], unit: "L", minQuantity: 50 },
    });
    flushSync();
    expect(target.querySelector(".chart-empty")).not.toBeNull();
    unmount(comp);
  });

  it("renders a line, area, and one point per transaction, sorted chronologically", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    // Deliberately out of chronological order -- the component must sort internally.
    const transactions = [
      makeTx({ id: "t3", timestamp: "2026-03-01T00:00:00Z", quantityAfter: 300 }),
      makeTx({ id: "t1", timestamp: "2026-01-01T00:00:00Z", quantityAfter: 100 }),
      makeTx({ id: "t2", timestamp: "2026-02-01T00:00:00Z", quantityAfter: 200 }),
    ];
    const comp = mount(ConsumableStockChart, {
      target,
      props: { transactions, unit: "L", minQuantity: 50 },
    });
    flushSync();

    expect(target.querySelectorAll("svg circle").length).toBe(3);
    const linePath = target.querySelector("path[stroke-width='2']");
    expect(linePath).not.toBeNull();
    const areaPath = target.querySelector("path[opacity='0.1']");
    expect(areaPath).not.toBeNull();

    // The line's first move-to point should correspond to the earliest
    // (Jan) transaction, not the first array element (Mar).
    const d = linePath!.getAttribute("d")!;
    const firstX = parseFloat(d.split(" ")[1]);
    const circles = Array.from(target.querySelectorAll("svg circle"));
    const xs = circles.map((c) => parseFloat(c.getAttribute("cx")!));
    expect(Math.min(...xs)).toBeCloseTo(firstX, 1);

    unmount(comp);
  });

  it("draws a dashed minimum-quantity threshold line when applicable", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableStockChart, {
      target,
      props: {
        transactions: [
          makeTx({ id: "t1", timestamp: "2026-01-01T00:00:00Z", quantityAfter: 100 }),
          makeTx({ id: "t2", timestamp: "2026-02-01T00:00:00Z", quantityAfter: 200 }),
        ],
        unit: "L",
        minQuantity: 50,
      },
    });
    flushSync();
    const dashed = target.querySelector("line[stroke-dasharray]");
    expect(dashed).not.toBeNull();
    unmount(comp);
  });

  it("omits the threshold line when minQuantity is 0", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableStockChart, {
      target,
      props: {
        transactions: [
          makeTx({ id: "t1", timestamp: "2026-01-01T00:00:00Z", quantityAfter: 100 }),
          makeTx({ id: "t2", timestamp: "2026-02-01T00:00:00Z", quantityAfter: 200 }),
        ],
        unit: "L",
        minQuantity: 0,
      },
    });
    flushSync();
    expect(target.querySelector("line[stroke-dasharray]")).toBeNull();
    unmount(comp);
  });

  it("shows a tooltip with the nearest point's date and quantity on pointer move", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableStockChart, {
      target,
      props: {
        transactions: [
          makeTx({ id: "t1", timestamp: "2026-01-01T00:00:00Z", quantityAfter: 100 }),
          makeTx({ id: "t2", timestamp: "2026-06-01T00:00:00Z", quantityAfter: 250 }),
        ],
        unit: "L",
        minQuantity: 50,
      },
    });
    flushSync();

    expect(target.querySelector(".chart-tooltip")).toBeNull();

    const svg = target.querySelector("svg")!;
    const rectStub = { left: 0, top: 0, width: 520, height: 200, right: 520, bottom: 200, x: 0, y: 0, toJSON() {} };
    svg.getBoundingClientRect = () => rectStub as DOMRect;

    // Near the right edge -- should snap to the later (June) point.
    svg.dispatchEvent(new MouseEvent("pointermove", { clientX: 510, clientY: 50, bubbles: true }));
    flushSync();

    const tooltip = target.querySelector(".chart-tooltip");
    expect(tooltip).not.toBeNull();
    expect(tooltip!.querySelector(".chart-tooltip-value")?.textContent).toContain("250");

    svg.dispatchEvent(new MouseEvent("pointerleave", { bubbles: true }));
    flushSync();
    expect(target.querySelector(".chart-tooltip")).toBeNull();

    unmount(comp);
  });
});
