import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeWorksWidget from "../src/lib/components/HomeWorksWidget.svelte";
import { createWorksStore } from "../src/lib/worksStore.svelte";

const sampleDoc = {
  version: 1,
  works: [
    { id: "w1", title: "Repaint fence", description: "", status: "done", categoryId: null, date: "2026-01-10", totalCost: 150, supplierId: null, notes: "", attachments: [], placement: null },
    { id: "w2", title: "Fix roof leak", description: "", status: "in_progress", categoryId: null, date: "2026-05-01", totalCost: 400, supplierId: null, notes: "", attachments: [], placement: null },
    { id: "w3", title: "New deck", description: "", status: "planned", categoryId: null, date: "2026-08-01", totalCost: null, supplierId: null, notes: "", attachments: [], placement: null },
  ],
};

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
  return createWorksStore();
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeWorksWidget", () => {
  it("shows counts per status", async () => {
    const worksStore = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const stats = Array.from(target.querySelectorAll(".stat-value")).map((el) => el.textContent);
    expect(stats).toEqual(["1", "1", "1"]);

    unmount(comp);
    target.remove();
  });

  it("shows the total cost across all works", async () => {
    const worksStore = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".sub")!.textContent).toContain("550");

    unmount(comp);
    target.remove();
  });

  it("lists the 5 most recent works, newest first", async () => {
    const worksStore = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const titles = Array.from(target.querySelectorAll(".title")).map((el) => el.textContent);
    expect(titles).toEqual(["New deck", "Fix roof leak", "Repaint fence"]);

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    const worksStore = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeWorksWidget, { target, props: { worksStore, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
