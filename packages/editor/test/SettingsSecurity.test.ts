import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsSecurity from "../src/lib/components/settings/SettingsSecurity.svelte";

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

function defaultOidcConfig() {
  return {
    enabled: false, provider_name: "", issuer: "", client_id: "",
    client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"],
  };
}

describe("SettingsSecurity", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  function setupFetch(overrides: Record<string, () => Promise<unknown>> = {}) {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      const key = `${opts?.method ?? "GET"} ${url}`;
      if (overrides[key]) return overrides[key]();
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  }

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    setupFetch();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders API Tokens, Users, and Single Sign-On for an admin", async () => {
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("API Tokens");
    expect(target.textContent).toContain("Users");
    expect(target.textContent).toContain("Single Sign-On");
    unmount(app);
  });

  it("hides Users and Single Sign-On for a non-admin but keeps API Tokens", async () => {
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("normal") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("API Tokens");
    expect(target.textContent).not.toContain("Single Sign-On");
    const cards = [...target.querySelectorAll(".ui-card")].map((c) => c.textContent);
    expect(cards.some((t) => t?.includes("New user"))).toBe(false);
    unmount(app);
  });

  it("creates an API token via POST /api/auth/tokens", async () => {
    setupFetch({
      "POST /api/auth/tokens": async () => ({
        ok: true,
        json: async () => ({ token: "abc123", info: { id: "t2", name: "Test", role: "ro", owner_id: "u1", created_at: "2026-07-02T11:00:00+00:00", last_used_at: null } }),
      }),
    });
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    flushSync();
    const newBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New token"))!;
    newBtn.click();
    flushSync();
    const nameInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    nameInput.value = "Test";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const createBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.trim() === "Create")!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    const postCalls = fetchMock.mock.calls.filter(
      ([url, opts]: [string, RequestInit | undefined]) => url === "/api/auth/tokens" && opts?.method === "POST",
    );
    expect(postCalls.length).toBe(1);
    unmount(app);
  });

  it("creates a user via POST /api/auth/users", async () => {
    setupFetch({
      "POST /api/auth/users": async () => ({
        ok: true,
        json: async () => ({ id: "u3", username: "bob", role: "normal", created_at: "2026-07-02T00:00:00+00:00" }),
      }),
    });
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New user"))!;
    btn.click();
    flushSync();
    const inputs = target.querySelectorAll(".ui-modal input");
    (inputs[0] as HTMLInputElement).value = "bob";
    inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
    (inputs[1] as HTMLInputElement).value = "bobpassword1";
    inputs[1].dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const createBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.includes("Create user"))!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const postCalls = fetchMock.mock.calls.filter(
      ([url, opts]: [string, RequestInit | undefined]) => url === "/api/auth/users" && opts?.method === "POST",
    );
    expect(postCalls.length).toBe(1);
    unmount(app);
  });

  it("saves SSO config via PUT /api/auth/oidc/config", async () => {
    setupFetch({
      "PUT /api/auth/oidc/config": async () => ({
        ok: true,
        json: async () => ({ ...defaultOidcConfig(), enabled: true, provider_name: "Keycloak" }),
      }),
    });
    const app = mount(SettingsSecurity, { target, props: { authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const ssoHeading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Single Sign-On")!;
    const ssoCard = ssoHeading.closest(".ui-card") as HTMLElement;
    const saveButtons = Array.from(ssoCard.querySelectorAll("button")).filter((b) => b.textContent?.trim() === "Save");
    saveButtons[saveButtons.length - 1].click();
    await new Promise((r) => setTimeout(r, 0));
    const putCall = fetchMock.mock.calls.find(
      (c: unknown[]) => c[0] === "/api/auth/oidc/config" && (c[1] as RequestInit)?.method === "PUT",
    );
    expect(putCall).toBeTruthy();
    unmount(app);
  });
});
