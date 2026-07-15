import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsIntegrations from "../src/lib/components/settings/SettingsIntegrations.svelte";

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

describe("SettingsIntegrations", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/mcp/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: true, json: async () => ({ enabled: true }) });
      }
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("shows the MCP Server card for admin", async () => {
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) },
    });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("MCP Server");
    unmount(app);
  });

  it("hides the MCP Server card for non-admin", () => {
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("normal"), importFromDonetick: vi.fn(async () => 0) },
    });
    flushSync();
    expect(target.querySelector(".ui-card")).toBeNull();
    unmount(app);
  });

  it("shows the connection URL once enabled", async () => {
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) },
    });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Connection URL");
    const checkbox = target.querySelector('input[type="checkbox"]') as HTMLInputElement;
    checkbox.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Connection URL");
    unmount(app);
  });

  function makeImportFromDonetick(impl: (token: string) => Promise<number>) {
    return vi.fn(impl);
  }

  it("shows the Donetick card for admin", () => {
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick: makeImportFromDonetick(async () => 0) },
    });
    flushSync();
    expect(target.textContent).toContain("Donetick");
    unmount(app);
  });

  it("hides the Donetick card for non-admin", () => {
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("normal"), importFromDonetick: makeImportFromDonetick(async () => 0) },
    });
    flushSync();
    expect(target.textContent).not.toContain("Donetick");
    unmount(app);
  });

  it("imports from Donetick and shows the count", async () => {
    const importFromDonetick = makeImportFromDonetick(async (token) => {
      expect(token).toBe("secret-token");
      return 3;
    });
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const tokenInput = target.querySelector('input[placeholder="API token"]') as HTMLInputElement;
    tokenInput.value = "secret-token";
    tokenInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(importFromDonetick).toHaveBeenCalledWith("secret-token");
    expect(target.textContent).toContain("3 imported");
    unmount(app);
  });

  it("shows an error message when the import fails", async () => {
    const importFromDonetick = makeImportFromDonetick(async () => { throw new Error("boom"); });
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const tokenInput = target.querySelector('input[placeholder="API token"]') as HTMLInputElement;
    tokenInput.value = "bad-token";
    tokenInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Failed");
    unmount(app);
  });
});
