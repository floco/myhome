import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeChoresWidget from "../src/lib/components/HomeChoresWidget.svelte";
import { createChoreStore } from "../src/lib/choreStore.svelte";

const sampleDoc = {
  version: 1,
  chores: [
    { id: "c1", donetickId: null, name: "🧹 Sweep", emoji: "🧹", periodDays: 14, nextDueDate: new Date(Date.now() - 5 * 86400000).toISOString(), description: "", frequencyType: "interval", frequency: 14, frequencyMetadata: {}, scheduleFromDue: false },
    { id: "c2", donetickId: null, name: "🪟 Windows", emoji: "🪟", periodDays: 365, nextDueDate: new Date(Date.now() + 300 * 86400000).toISOString(), description: "", frequencyType: "interval", frequency: 365, frequencyMetadata: {}, scheduleFromDue: false },
  ],
  assignments: [
    { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 2 }, nextDueDate: new Date(Date.now() - 5 * 86400000).toISOString() },
    { id: "a2", choreId: "c2", roomId: null, position: null, nextDueDate: new Date(Date.now() + 300 * 86400000).toISOString() },
  ],
  completions: [],
};

const HOME = "home-123";
const getHomeId = () => HOME;

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }));
  return createChoreStore(getHomeId);
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeChoresWidget", () => {
  it("shows the active and overdue counts", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.textContent).toContain("2");
    expect(target.querySelector(".stat-item.overdue")!.textContent).toContain("1");

    unmount(comp);
    target.remove();
  });

  it("renders the most urgent assignment first", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const names = Array.from(target.querySelectorAll(".name")).map((el) => el.textContent);
    expect(names[0]).toBe("Sweep");

    unmount(comp);
    target.remove();
  });

  it("quick-completing a row calls store.completeAssignment", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
    flushSync();
    await tick();

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/complete"),
      expect.objectContaining({ method: "POST" })
    );

    unmount(comp);
    target.remove();
  });

  it("clicking the widget body calls onnavigate", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeChoresWidget, { target, props: { store, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
