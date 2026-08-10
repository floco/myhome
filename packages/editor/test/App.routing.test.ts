import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";
import { setNavGuard } from "../src/lib/navGuard";

function stubFetch404() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (url === "/api/auth/me") {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({ id: "u1", username: "admin", role: "admin" }),
        });
      }
      return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
    }),
  );
}

async function mountAndLoad(
  target: HTMLElement,
  route: string,
): Promise<ReturnType<typeof mount>> {
  window.location.hash = route;
  const app = mount(App, { target });
  await tick();
  await tick();
  await tick();  // extra tick for authStore init
  flushSync();
  return app;
}

describe("App — home dashboard routing", () => {
  beforeEach(() => {
    stubFetch404();
  });

  it("renders the floor plan editor at #/plan", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target, "#/plan");

    expect(target.querySelector("svg.canvas")).not.toBeNull();
    expect(target.querySelector(".home-page")).toBeNull();

    unmount(app);
    target.remove();
  });

  it("renders the home dashboard at the default route", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target, "#/");

    expect(target.querySelector(".home-page")).not.toBeNull();
    // HomeMapWidget renders Canvas (svg.canvas is present) — check toolbar is absent instead
    expect(target.querySelector(".toolbar")).toBeNull();

    unmount(app);
    target.remove();
  });
});

describe("App — nav guard integration", () => {
  beforeEach(() => {
    stubFetch404();
  });

  it("stays on the KB route when a registered nav guard rejects navigation, then navigates once the guard is cleared", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target, "#/kb");

    let resolveGuard!: (ok: boolean) => void;
    setNavGuard(() => new Promise((resolve) => { resolveGuard = resolve; }));

    // jsdom dispatches "hashchange" as a queued task, not synchronously —
    // give it a turn before asserting (same pattern as
    // CommandPalette.integration.test.ts's hashchange-dependent assertions).
    window.location.hash = "#/costs";
    await new Promise((r) => setTimeout(r, 0));
    await tick();
    flushSync();

    expect(window.location.hash).toBe("#/kb");

    resolveGuard(true);
    await new Promise((r) => setTimeout(r, 0));
    await tick();
    flushSync();

    expect(window.location.hash).toBe("#/costs");

    setNavGuard(null);
    unmount(app);
    target.remove();
  });
});
