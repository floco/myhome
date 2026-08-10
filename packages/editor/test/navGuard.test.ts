import { describe, it, expect, afterEach } from "vitest";
import { setNavGuard, createGuardedHashRouter } from "../src/lib/navGuard";

afterEach(() => setNavGuard(null));

describe("navGuard — createGuardedHashRouter", () => {
  it("routes immediately when no guard is registered", () => {
    let hash = "#/kb/a";
    const routes: string[] = [];
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; },
      onRoute: (h) => { routes.push(h); },
    });
    hash = "#/costs";
    router.handleHashChange();
    expect(routes).toEqual(["#/costs"]);
    expect(hash).toBe("#/costs");
  });

  it("reverts the hash when a guard is registered, then replays the target hash once the guard resolves true", async () => {
    const routes: string[] = [];
    let hash = "#/kb/a";
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; router.handleHashChange(); },
      onRoute: (h) => { routes.push(h); },
    });
    let resolveGuard!: (ok: boolean) => void;
    setNavGuard(() => new Promise((resolve) => { resolveGuard = resolve; }));

    hash = "#/costs"; // simulates the browser having already applied the navigation
    router.handleHashChange();

    // Reverted synchronously; the fake setHash echoes back into the router,
    // which recognizes its own revert and just resyncs onRoute.
    expect(hash).toBe("#/kb/a");
    expect(routes).toEqual(["#/kb/a"]);

    resolveGuard(true);
    await Promise.resolve();
    await Promise.resolve();

    expect(hash).toBe("#/costs");
    expect(routes).toEqual(["#/kb/a", "#/costs"]);
  });

  it("stays on the current route when the guard resolves false", async () => {
    const routes: string[] = [];
    let hash = "#/kb/a";
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; router.handleHashChange(); },
      onRoute: (h) => { routes.push(h); },
    });
    setNavGuard(async () => false);

    hash = "#/costs";
    router.handleHashChange();
    await Promise.resolve();
    await Promise.resolve();

    expect(hash).toBe("#/kb/a");
    expect(routes).toEqual(["#/kb/a"]);
  });

  it("does nothing when the new hash equals the current route (no-op navigation)", () => {
    const routes: string[] = [];
    let hash = "#/kb/a";
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; },
      onRoute: (h) => { routes.push(h); },
    });
    setNavGuard(async () => false); // guard present but should never be consulted
    router.handleHashChange();
    expect(routes).toEqual(["#/kb/a"]);
  });
});
