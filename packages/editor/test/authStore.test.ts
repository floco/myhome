import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushSync } from "svelte";
import { createAuthStore } from "../src/lib/authStore.svelte";

describe("authStore", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("starts with checking=true and user=null", () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 401 } as Response);
    const store = createAuthStore();
    expect(store.checking).toBe(true);
    expect(store.user).toBeNull();
  });

  it("sets user when /me returns 200", async () => {
    const mockUser = { id: "u1", username: "admin", role: "admin" };
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => mockUser } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(store.user).toEqual(mockUser);
    expect(store.checking).toBe(false);
  });

  it("sets user=null and checking=false when /me returns 401", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 401 } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(store.user).toBeNull();
    expect(store.checking).toBe(false);
  });

  it("login() calls /api/auth/login and sets user", async () => {
    const mockUser = { id: "u1", username: "alice", role: "normal" };
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response)  // init /me
      .mockResolvedValueOnce({ ok: true, json: async () => mockUser } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const result = await store.login("alice", "alicepass");
    flushSync();
    expect(store.user).toEqual(mockUser);
    expect(result).toEqual(mockUser);
  });

  it("login() throws on 401 and does not set user", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response)  // init
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response);  // login
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    await expect(store.login("x", "y")).rejects.toThrow("Invalid credentials");
    expect(store.user).toBeNull();
  });

  it("logout() calls /api/auth/logout and clears user", async () => {
    const mockUser = { id: "u1", username: "admin", role: "admin" };
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: true, json: async () => mockUser } as Response)
      .mockResolvedValueOnce({ ok: true } as Response);
    const store = createAuthStore();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    await store.logout();
    flushSync();
    expect(store.user).toBeNull();
    const logoutCall = vi.mocked(fetch).mock.calls.find((c) => c[0] === "/api/auth/logout");
    expect(logoutCall).toBeTruthy();
  });
});
