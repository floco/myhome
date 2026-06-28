import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

function stubFetch404() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() =>
      Promise.resolve({ ok: false, status: 404, json: async () => undefined }),
    ),
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
