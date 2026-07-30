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
    localStorage.clear();
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

  function makeImportFromDonetick(impl: (token: string, url: string) => Promise<number>) {
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
    const importFromDonetick = makeImportFromDonetick(async (token, url) => {
      expect(token).toBe("secret-token");
      expect(url).toBe("https://donetick.example.com");
      return 3;
    });
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const urlInput = target.querySelector('input[placeholder^="Donetick URL"]') as HTMLInputElement;
    urlInput.value = "https://donetick.example.com";
    urlInput.dispatchEvent(new Event("input", { bubbles: true }));
    const tokenInput = target.querySelector('input[placeholder="API token"]') as HTMLInputElement;
    tokenInput.value = "secret-token";
    tokenInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(importFromDonetick).toHaveBeenCalledWith("secret-token", "https://donetick.example.com");
    expect(target.textContent).toContain("3 imported");
    unmount(app);
  });

  it("requires a URL before importing", async () => {
    const importFromDonetick = makeImportFromDonetick(async () => 0);
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(importFromDonetick).not.toHaveBeenCalled();
    expect(target.textContent).toContain("Donetick URL is required");
    unmount(app);
  });

  it("shows the backend's actual error message when the import fails", async () => {
    const importFromDonetick = makeImportFromDonetick(async () => {
      throw new Error("Donetick error: [Errno -2] Name or service not known");
    });
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const urlInput = target.querySelector('input[placeholder^="Donetick URL"]') as HTMLInputElement;
    urlInput.value = "https://donetick.example.com";
    urlInput.dispatchEvent(new Event("input", { bubbles: true }));
    const tokenInput = target.querySelector('input[placeholder="API token"]') as HTMLInputElement;
    tokenInput.value = "bad-token";
    tokenInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Donetick error: [Errno -2] Name or service not known");
    unmount(app);
  });

  it("falls back to a generic message when the thrown error has no message", async () => {
    const importFromDonetick = makeImportFromDonetick(async () => { throw new Error(); });
    const app = mount(SettingsIntegrations, {
      target,
      props: { authStore: makeAuthStore("admin"), importFromDonetick },
    });
    flushSync();
    const urlInput = target.querySelector('input[placeholder^="Donetick URL"]') as HTMLInputElement;
    urlInput.value = "https://donetick.example.com";
    urlInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const importButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Import") as HTMLButtonElement;
    importButton.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Failed");
    unmount(app);
  });
});
