import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

const HOME = { id: "home-1", name: "Main House", type: "existing", enabledModules: [], createdAt: "2026-01-01T00:00:00.000Z" };

const HOUSE_DOC = {
  version: 1,
  house: { name: "Main House", units: "m", gridSnap: 0.1 },
  floors: [
    {
      id: "gf-1",
      name: "Ground Floor",
      order: 0,
      walls: [
        { id: "w1", type: "wall", thickness: 0.1, start: { x: 0, y: 0 }, end: { x: 4, y: 0 } },
        { id: "w2", type: "wall", thickness: 0.1, start: { x: 4, y: 0 }, end: { x: 4, y: 3 } },
        { id: "w3", type: "wall", thickness: 0.1, start: { x: 4, y: 3 }, end: { x: 0, y: 3 } },
        { id: "w4", type: "wall", thickness: 0.1, start: { x: 0, y: 3 }, end: { x: 0, y: 0 } },
      ],
      openings: [],
      rooms: [
        { id: "room-1", label: "Room 1", haAreaId: null, polygon: [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 3 }, { x: 0, y: 3 }], areaM2: 12 },
      ],
      furnitureObjects: [],
    },
  ],
  currentFloorId: "gf-1",
};

const CHORE_DOC = {
  version: 1,
  chores: [{ id: "c1", donetickId: null, name: "Water plants", emoji: "💧", periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {}, scheduleFromDue: false, nextDueDate: "2026-07-01", description: "" }],
  assignments: [{ id: "a1", choreId: "c1", roomId: "room-1", position: { x: 2, y: 1.5 }, nextDueDate: "2026-07-01", label: null }],
  completions: [],
};

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const handlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      "/api/homes": [HOME],
      [`/api/homes/${HOME.id}/house`]: HOUSE_DOC,
      [`/api/homes/${HOME.id}/chores`]: CHORE_DOC,
    };
    if (url in handlers) {
      return Promise.resolve({ ok: true, status: 200, json: async () => handlers[url] });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

async function mountApp(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  window.location.hash = "#/plan";
  const app = mount(App, { target });
  for (let i = 0; i < 10; i++) await tick();
  flushSync();
  return app;
}

function findChoreBadge(target: HTMLElement): SVGGElement | undefined {
  return Array.from(target.querySelectorAll("g")).find(
    (g) => g.querySelector("text")?.textContent === "💧",
  ) as SVGGElement | undefined;
}

describe("App — badge popup details button", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) { unmount(app); app = undefined; }
    target?.remove();
    vi.unstubAllGlobals();
  });

  it("opens the full ChoreEditModal when the badge popup's details button is clicked", async () => {
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    (target.querySelector('button[title="Toggle map layers"]') as HTMLButtonElement).click();
    await tick();
    flushSync();
    const choresRow = Array.from(document.querySelectorAll(".layer-row")).find(
      (r) => r.textContent?.includes("Chores"),
    ) as HTMLElement;
    (choresRow.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
    await tick();
    flushSync();

    const badge = findChoreBadge(target);
    expect(badge).toBeDefined();
    badge!.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1, clientX: 600, clientY: 450 }));
    flushSync();
    badge!.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1, clientX: 600, clientY: 450 }));
    flushSync();

    expect(target.querySelector(".popup-name")?.textContent).toBe("Water plants");
    const detailsBtn = target.querySelector(".details-btn") as HTMLButtonElement;
    expect(detailsBtn).not.toBeNull();

    detailsBtn.click();
    flushSync();

    expect(target.querySelector(".popup-name")).toBeNull();
    expect(target.querySelectorAll(".tab").length).toBeGreaterThan(0);
  });
});
