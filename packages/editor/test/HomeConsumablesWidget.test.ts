import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeConsumablesWidget from "../src/lib/components/HomeConsumablesWidget.svelte";
import { createConsumableStore } from "../src/lib/consumableStore.svelte";

const allOkDoc = {
  version: 1,
  consumables: [
    {
      id: "c1",
      name: "Batteries",
      emoji: "🔋",
      unit: "count",
      quantity: 10,
      minQuantity: 4,
      categoryId: null,
      description: "",
      placement: null,
    },
  ],
  transactions: [],
};

const alertDoc = {
  version: 1,
  consumables: [
    {
      id: "c1",
      name: "Batteries",
      emoji: "🔋",
      unit: "count",
      quantity: 0,
      minQuantity: 4,
      categoryId: null,
      description: "",
      placement: null,
    },
    {
      id: "c2",
      name: "Dish Soap",
      emoji: "🧴",
      unit: "mL",
      quantity: 50,
      minQuantity: 100,
      categoryId: null,
      description: "",
      placement: null,
    },
    {
      id: "c3",
      name: "Toothpaste",
      emoji: "🪥",
      unit: "g",
      quantity: 200,
      minQuantity: 50,
      categoryId: null,
      description: "",
      placement: null,
    },
  ],
  transactions: [],
};

const HOME = "home-123";
const getHomeId = () => HOME;

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}
afterEach(() => vi.unstubAllGlobals());

function makeStore(doc: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }),
  );
  return createConsumableStore(getHomeId);
}

describe("HomeConsumablesWidget", () => {
  it("renders nothing when all items are OK", async () => {
    const consumableStore = makeStore(allOkDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, {
      target,
      props: { consumableStore, onnavigate: vi.fn() },
    });
    await tick();
    flushSync();
    expect(target.querySelector(".widget")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("shows empty and low items only", async () => {
    const consumableStore = makeStore(alertDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, {
      target,
      props: { consumableStore, onnavigate: vi.fn() },
    });
    await tick();
    flushSync();
    const text = target.textContent ?? "";
    expect(text).toContain("Batteries");
    expect(text).toContain("Dish Soap");
    expect(text).not.toContain("Toothpaste");
    unmount(comp);
    target.remove();
  });

  it("shows empty and low count pills", async () => {
    const consumableStore = makeStore(alertDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, {
      target,
      props: { consumableStore, onnavigate: vi.fn() },
    });
    await tick();
    flushSync();
    const text = target.textContent ?? "";
    expect(text).toContain("1 empty");
    expect(text).toContain("1 low");
    unmount(comp);
    target.remove();
  });

  it("clicking widget calls onnavigate", async () => {
    const consumableStore = makeStore(alertDoc);
    await makeTick();
    const onnavigate = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeConsumablesWidget, {
      target,
      props: { consumableStore, onnavigate },
    });
    await tick();
    flushSync();
    (target.querySelector(".widget") as HTMLElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true }),
    );
    flushSync();
    expect(onnavigate).toHaveBeenCalledOnce();
    unmount(comp);
    target.remove();
  });
});
