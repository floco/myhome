import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import WorksTimeline from "../src/lib/components/WorksTimeline.svelte";
import type { Work } from "../src/lib/worksStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeWork(overrides: Partial<Work> = {}): Work {
  return {
    id: "w1", title: "Fix roof leak", description: "", status: "planned",
    categoryId: null, date: "2026-06-10T12:00:00.000Z", totalCost: null,
    supplierId: null, notes: "", attachments: [], placement: null,
    ...overrides,
  };
}

describe("WorksTimeline", () => {
  it("renders zero dots and does not crash with an empty works list", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works: [] } });
    flushSync();

    expect(target.querySelectorAll("circle")).toHaveLength(0);

    unmount(comp);
  });

  it("renders one dot per work, colored by status", () => {
    const works = [
      makeWork({ id: "w1", status: "done", date: "2024-01-15T00:00:00.000Z" }),
      makeWork({ id: "w2", status: "in_progress", date: "2025-06-01T00:00:00.000Z" }),
      makeWork({ id: "w3", status: "planned", date: "2026-12-01T00:00:00.000Z" }),
    ];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    const circles = target.querySelectorAll("circle");
    expect(circles).toHaveLength(3);
    const fills = Array.from(circles).map((c) => c.getAttribute("fill"));
    expect(fills).toEqual(["#33aa66", "#3388cc", "#cc8833"]);

    unmount(comp);
  });

  it("renders a single dot without crashing when there is only one work", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works: [makeWork()] } });
    flushSync();

    expect(target.querySelectorAll("circle")).toHaveLength(1);

    unmount(comp);
  });

  it("staggers dots that share the exact same date onto different lanes", () => {
    const sameDate = "2026-03-01T00:00:00.000Z";
    const works = Array.from({ length: 5 }, (_, i) => makeWork({ id: `w${i}`, date: sameDate }));
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    const circles = Array.from(target.querySelectorAll("circle"));
    expect(circles).toHaveLength(5);
    const yValues = new Set(circles.map((c) => c.getAttribute("cy")));
    expect(yValues.size).toBeGreaterThan(1);

    unmount(comp);
  });

  it("calls onworkclick with the work's id when its dot is clicked", () => {
    const onworkclick = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, {
      target,
      props: { works: [makeWork({ id: "w42" })], onworkclick },
    });
    flushSync();

    const circle = target.querySelector("circle") as SVGCircleElement;
    circle.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onworkclick).toHaveBeenCalledWith("w42");

    unmount(comp);
  });

  it("shows a dashed today-marker line when works span the present", () => {
    const past = new Date(Date.now() - 30 * 86400000).toISOString();
    const future = new Date(Date.now() + 30 * 86400000).toISOString();
    const works = [makeWork({ id: "w1", date: past, status: "done" }), makeWork({ id: "w2", date: future, status: "planned" })];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    expect(target.querySelector('line[stroke-dasharray="3 3"]')).not.toBeNull();

    unmount(comp);
  });

  it("omits the today-marker line when all works are in the past", () => {
    const older = new Date(Date.now() - 60 * 86400000).toISOString();
    const newer = new Date(Date.now() - 30 * 86400000).toISOString();
    const works = [makeWork({ id: "w1", date: older, status: "done" }), makeWork({ id: "w2", date: newer, status: "done" })];
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(WorksTimeline, { target, props: { works } });
    flushSync();

    expect(target.querySelector('line[stroke-dasharray="3 3"]')).toBeNull();

    unmount(comp);
  });
});
