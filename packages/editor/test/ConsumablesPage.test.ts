import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import ConsumablesPage from "../src/lib/components/ConsumablesPage.svelte";
import { createConsumableStore } from "../src/lib/consumableStore.svelte";

const sampleDoc = {
  version: 1,
  consumables: [
    {
      id: "c1",
      name: "AA Batteries",
      emoji: "🔋",
      unit: "count",
      quantity: 6.0,
      minQuantity: 4.0,
      categoryId: null,
      description: "",
      placement: null,
    },
    {
      id: "c2",
      name: "Dish Soap",
      emoji: "🧴",
      unit: "mL",
      quantity: 0.0,
      minQuantity: 100.0,
      categoryId: "cat1",
      description: "",
      placement: null,
    },
    {
      id: "c3",
      name: "Toothpaste",
      emoji: "🪥",
      unit: "g",
      quantity: 50.0,
      minQuantity: 100.0,
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

function makeStore() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sampleDoc }),
  );
  return createConsumableStore(getHomeId);
}

afterEach(() => vi.unstubAllGlobals());

describe("ConsumablesPage", () => {
  it("renders all consumables in the table", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: {
        store,
        settingsStore: { consumableCategories: [], consumableUnits: [] },
        onplaceonmap: vi.fn(),
      },
    });
    await tick();
    flushSync();
    expect(target.querySelectorAll("tbody tr").length).toBe(3);
    unmount(comp);
    target.remove();
  });

  it("filters to low/empty items with needs-attention toggle", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: {
        store,
        settingsStore: { consumableCategories: [], consumableUnits: [] },
        onplaceonmap: vi.fn(),
      },
    });
    await tick();
    flushSync();
    const attentionBtn = Array.from(target.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("⚠"),
    );
    if (attentionBtn) {
      attentionBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      flushSync();
    }
    const rows = target.querySelectorAll("tbody tr");
    const text = Array.from(rows)
      .map((r) => r.textContent ?? "")
      .join(" ");
    expect(text).toContain("Dish Soap");
    expect(text).toContain("Toothpaste");
    unmount(comp);
    target.remove();
  });

  it("shows empty state when no consumables", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ version: 1, consumables: [], transactions: [] }),
      }),
    );
    const store = createConsumableStore(getHomeId);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumablesPage, {
      target,
      props: {
        store,
        settingsStore: { consumableCategories: [], consumableUnits: [] },
        onplaceonmap: vi.fn(),
      },
    });
    await tick();
    flushSync();
    expect(target.querySelector(".empty")).not.toBeNull();
    unmount(comp);
    target.remove();
  });
});
