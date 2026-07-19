import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationsMatrix from "../src/lib/components/LocationsMatrix.svelte";
import { createLocationsStore } from "../src/lib/locationsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

const sampleDoc = {
  version: 1,
  criteria: [
    { id: "c1", name: "Cost of Living", description: "Land, construction, everyday costs", weight: "high" },
    { id: "c2", name: "Safety", description: "", weight: "medium" },
  ],
  locations: [
    { id: "l1", name: "Nantes", emoji: "🇫🇷" },
    { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
  ],
  ratings: [
    { locationId: "l1", criterionId: "c1", score: 2, note: "pricier" },
    { locationId: "l2", criterionId: "c1", score: 5, note: "cheap" },
  ],
};

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

function enterEditMode(el: HTMLElement): void {
  const editBtn = Array.from(el.querySelectorAll(".mode-btn")).find((b) => b.textContent === "✏️ Edit") as HTMLButtonElement;
  editBtn.click();
  flushSync();
}

afterEach(() => vi.unstubAllGlobals());

describe("LocationsMatrix", () => {
  it("renders one column per location and one row per criterion", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    expect(el.querySelectorAll(".location-header").length).toBe(2);
    expect(el.querySelectorAll("tbody tr").length).toBe(2);
    unmount(comp);
    el.remove();
  });

  it("highlights the best-rated cell in each criterion row", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    const costRow = Array.from(el.querySelectorAll("tbody tr"))[0];
    const bestCells = costRow.querySelectorAll("td.rating-cell.best");
    expect(bestCells.length).toBe(1);
    expect(bestCells[0].querySelectorAll(".star.filled").length).toBe(5);
    unmount(comp);
    el.remove();
  });

  it("clicking a cell opens the rating popup", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    const safetyRow = Array.from(el.querySelectorAll("tbody tr"))[1];
    const cell = safetyRow.querySelector("td.rating-cell") as HTMLElement;
    cell.click();
    flushSync();
    expect(document.querySelector(".popup-title")).not.toBeNull();
    unmount(comp);
    el.remove();
  });

  it("adding a location opens the modal via the + trigger and POSTs to the locations endpoint", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    enterEditMode(el);
    (el.querySelector(".add-header .add-btn") as HTMLButtonElement).click();
    flushSync();
    const nameInput = document.querySelector(".ui-input") as HTMLInputElement;
    nameInput.value = "Zagreb";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const addBtn = Array.from(document.querySelectorAll("button")).find((b) => b.textContent === "Add") as HTMLButtonElement;
    addBtn.click();
    await tick();
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/locations`,
      expect.objectContaining({ method: "POST" }),
    );
    unmount(comp);
    el.remove();
  });

  it("deleting a criterion requires a confirm click", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    enterEditMode(el);
    const costRow = Array.from(el.querySelectorAll("tbody tr"))[0];
    const deleteBtn = costRow.querySelector(".criterion-cell button[title='Delete']") as HTMLButtonElement;
    deleteBtn.click();
    flushSync();
    expect(costRow.querySelector(".confirm-text")).not.toBeNull();
    unmount(comp);
    el.remove();
  });

  it("View mode hides structural controls but rating cells stay clickable", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    expect(el.querySelector(".header-actions")).toBeNull();
    expect(el.querySelector(".row-actions")).toBeNull();
    expect(el.querySelector(".add-header")).toBeNull();
    expect(el.querySelector(".corner .add-btn")).toBeNull();

    const cell = el.querySelector("td.rating-cell") as HTMLElement;
    cell.click();
    flushSync();
    expect(document.querySelector(".popup-title")).not.toBeNull();
    unmount(comp);
    el.remove();
  });

  it("Edit mode shows structural controls", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    enterEditMode(el);
    expect(el.querySelectorAll(".header-actions").length).toBe(2);
    expect(el.querySelectorAll(".row-actions").length).toBe(2);
    expect(el.querySelector(".add-header")).not.toBeNull();
    expect(el.querySelector(".corner .add-btn")).not.toBeNull();
    unmount(comp);
    el.remove();
  });
});
