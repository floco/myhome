import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsPage from "../src/lib/components/SettingsPage.svelte";

function makeStore() {
  return {
    costCategories: [],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
    consumableUnits: [],
    consumableCategories: [],
    notificationSettings: {
      enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
      haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
    },
    loaded: true,
    loadError: null,
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
    placeCostCategory: vi.fn(),
    updateNotificationSettings: vi.fn(),
  };
}

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

function mockBoilerplateEndpoints(url: string): { ok: boolean; json: () => Promise<unknown> } | null {
  if (url === "/api/backup/config") {
    return {
      ok: true,
      json: async () => ({
        enabled: false, frequency: "daily", time: "03:00",
        dayOfWeek: 7, dayOfMonth: 1, retentionCount: 7,
      }),
    };
  }
  if (url === "/api/backup/scheduled") {
    return { ok: true, json: async () => [] };
  }
  return null;
}

describe("SettingsPage — Backup & Restore", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:fake");
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the Backup & Restore card with both buttons", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    expect(target.textContent).toContain("Backup & Restore");
    expect(target.textContent).toContain("Download Backup");
    expect(target.textContent).toContain("Restore from Backup");
    unmount(app);
  });

  it("has a hidden file input that accepts .zip files", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();
    expect(fileInput.accept).toBe(".zip");
    unmount(app);
  });

  it("calls GET /api/backup/download when Download Backup is clicked", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response("fake-zip-content", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="myhome-backup-2026-06-29.zip"' },
      }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();

    const btn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.includes("Download Backup")
    )!;
    btn.click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith("/api/backup/download");
    unmount(app);
  });

  it("shows confirmation modal when a zip file is selected for restore", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("This will replace all current data");
    unmount(app);
  });

  it("calls POST /api/backup/restore with FormData when Restore is confirmed", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 204 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const restoreBtn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.trim() === "Restore"
    )!;
    restoreBtn.click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/restore",
      expect.objectContaining({ method: "POST" })
    );
    unmount(app);
  });

  it("dismisses modal when Cancel is clicked without calling fetch", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const cancelBtn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.trim() === "Cancel"
    )!;
    cancelBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalledWith("/api/backup/restore", expect.anything());
    unmount(app);
  });

  it("renders the Scheduled Backups section with defaults", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("Scheduled Backups");
    expect((target.querySelector(".backup-enable-toggle") as HTMLInputElement).checked).toBe(false);
    unmount(app);
  });

  it("shows day-of-week only for weekly and day-of-month only for monthly", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/backup/config") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            enabled: true, frequency: "weekly", time: "03:00",
            dayOfWeek: 3, dayOfMonth: 1, retentionCount: 7,
          }),
        });
      }
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const labels = Array.from(target.querySelectorAll(".modal-label")).map((el) => el.textContent);
    expect(labels).toContain("Day of week");
    expect(labels).not.toContain("Day of month");

    unmount(app);
  });

  it("saves scheduled backup config via PUT /api/backup/config", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const enableToggle = target.querySelector(".backup-enable-toggle") as HTMLInputElement;
    enableToggle.click();
    flushSync();

    const backupCard = enableToggle.closest(".ui-card") as HTMLElement;
    const saveBtn = Array.from(backupCard.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Save")!;
    (saveBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/config",
      expect.objectContaining({ method: "PUT" }),
    );
    unmount(app);
  });

  it("Run backup now calls POST /api/backup/scheduled/run", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const runBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Run backup now"))!;
    (runBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/scheduled/run",
      expect.objectContaining({ method: "POST" }),
    );
    unmount(app);
  });

  it("renders the scheduled backups list and deletes an entry after confirmation", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/backup/scheduled") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { filename: "myhome-backup-20260701-030000.zip", createdAt: "2026-07-01T03:00:00Z", sizeBytes: 2048 },
          ],
        });
      }
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("2.0 KB");

    const deleteBtn = target.querySelector(".backup-row .icon-action.danger") as HTMLButtonElement;
    deleteBtn.click();
    flushSync();
    expect(target.textContent).toContain("Delete?");

    const confirmBtn = Array.from(target.querySelectorAll(".backup-row .icon-action.danger")).find((b) => b.textContent === "✓")!;
    (confirmBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/scheduled/myhome-backup-20260701-030000.zip",
      expect.objectContaining({ method: "DELETE" }),
    );
    unmount(app);
  });
});

describe("SettingsPage — API Tokens", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: "t1", name: "MCP Server", role: "ro", owner_id: "u1",
              created_at: "2026-07-02T10:00:00+00:00", last_used_at: null },
          ],
        });
      }
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the API Tokens section", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    expect(target.textContent).toContain("API Tokens");
    unmount(app);
  });

  it("shows token list after load", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("MCP Server");
    unmount(app);
  });

  it("opens New Token modal when button clicked", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New token"))!;
    btn.click();
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("Token name");
    unmount(app);
  });

  it("calls POST /api/auth/tokens when Create is clicked", async () => {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens" && opts?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            token: "abc123def456",
            info: { id: "t2", name: "Test", role: "ro", owner_id: "u1",
                    created_at: "2026-07-02T11:00:00+00:00", last_used_at: null },
          }),
        });
      }
      if (url === "/api/auth/tokens") {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url === "/api/auth/users") {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;

    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    const newBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New token"))!;
    newBtn.click();
    flushSync();

    const nameInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    nameInput.value = "Test";
    nameInput.dispatchEvent(new Event("input"));
    flushSync();

    const createBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.trim() === "Create")!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const postCalls = fetchMock.mock.calls.filter(
      ([url, opts]: [string, RequestInit | undefined]) => url === "/api/auth/tokens" && opts?.method === "POST"
    );
    expect(postCalls.length).toBe(1);
    unmount(app);
  });
});

describe("SettingsPage — Users tab (admin only)", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: "u1", username: "admin", role: "admin", created_at: "2026-01-01T00:00:00+00:00" },
            { id: "u2", username: "alice", role: "normal", created_at: "2026-01-02T00:00:00+00:00" },
          ],
        });
      }
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("shows Users section for admin", async () => {
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("admin") },
    });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Users");
    expect(target.textContent).toContain("alice");
    unmount(app);
  });

  it("hides Users section for non-admin", () => {
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("normal") },
    });
    flushSync();
    const cards = [...target.querySelectorAll(".ui-card")].map((c) => c.textContent);
    expect(cards.some((t) => t?.includes("New user"))).toBe(false);
    unmount(app);
  });

  it("opens New User modal when button clicked", async () => {
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("admin") },
    });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New user"))!;
    btn.click();
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("Username");
    unmount(app);
  });

  it("calls POST /api/auth/users when Create user is clicked", async () => {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users" && opts?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: "u3", username: "bob", role: "normal", created_at: "2026-07-02T00:00:00+00:00" }),
        });
      }
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    globalThis.fetch = fetchMock;

    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore("admin") },
    });
    flushSync();

    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("New user"))!;
    btn.click();
    flushSync();

    const inputs = target.querySelectorAll(".ui-modal input");
    (inputs[0] as HTMLInputElement).value = "bob";
    inputs[0].dispatchEvent(new Event("input"));
    (inputs[1] as HTMLInputElement).value = "bobpassword1";
    inputs[1].dispatchEvent(new Event("input"));
    flushSync();

    const createBtn = [...target.querySelectorAll(".ui-modal button")].find(
      (b) => b.textContent?.includes("Create user"),
    )!;
    createBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const postCalls = fetchMock.mock.calls.filter(
      ([url, opts]: [string, RequestInit | undefined]) => url === "/api/auth/users" && opts?.method === "POST"
    );
    expect(postCalls.length).toBe(1);
    unmount(app);
  });
});

describe("SettingsPage — MCP Server (admin only)", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("shows the MCP Server card for admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("MCP Server");
    unmount(app);
  });

  it("hides the MCP Server card for non-admin", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal") } });
    flushSync();
    const cards = [...target.querySelectorAll(".ui-card")].map((c) => c.textContent);
    expect(cards.some((t) => t?.includes("MCP Server"))).toBe(false);
    unmount(app);
  });

  it("does not show the connection URL while disabled", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Connection URL");
    unmount(app);
  });

  it("shows the connection URL once enabled", async () => {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: true, json: async () => ({ enabled: true }) });
      }
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;

    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const checkbox = [...target.querySelectorAll('input[type="checkbox"]')].find(
      (el) => el.closest(".ui-card")?.textContent?.includes("MCP Server"),
    ) as HTMLInputElement;
    checkbox.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("Connection URL");
    unmount(app);
  });
});

describe("SettingsPage — Single Sign-On", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  function defaultOidcConfig() {
    return {
      enabled: false, provider_name: "", issuer: "", client_id: "",
      client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"],
    };
  }

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the Single Sign-On card for an admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Single Sign-On");
    unmount(app);
  });

  it("does not render the Single Sign-On card for a non-admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Single Sign-On");
    unmount(app);
  });

  it("saves config via PUT /api/auth/oidc/config", async () => {
    fetchMock.mockImplementation((url: string, opts?: RequestInit) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config" && (!opts || opts.method === undefined)) {
        return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      }
      if (url === "/api/auth/oidc/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: true, json: async () => ({ ...defaultOidcConfig(), enabled: true, provider_name: "Keycloak" }) });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const ssoHeading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Single Sign-On")!;
    const ssoCard = ssoHeading.closest(".ui-card") as HTMLElement;
    const saveButtons = Array.from(ssoCard.querySelectorAll("button")).filter(b => b.textContent?.trim() === "Save");
    expect(saveButtons.length).toBeGreaterThan(0);
    saveButtons[saveButtons.length - 1].click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const putCall = fetchMock.mock.calls.find(
      (c: unknown[]) => c[0] === "/api/auth/oidc/config" && (c[1] as RequestInit)?.method === "PUT",
    );
    expect(putCall).toBeTruthy();
    unmount(app);
  });

  it("shows an error message when save fails", async () => {
    fetchMock.mockImplementation((url: string, opts?: RequestInit) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: false, status: 422, json: async () => ({ detail: "Could not reach issuer" }) });
      }
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => defaultOidcConfig() });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const ssoHeading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Single Sign-On")!;
    const ssoCard = ssoHeading.closest(".ui-card") as HTMLElement;
    const saveButtons = Array.from(ssoCard.querySelectorAll("button")).filter(b => b.textContent?.trim() === "Save");
    saveButtons[saveButtons.length - 1].click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("Could not reach issuer");
    unmount(app);
  });
});

describe("SettingsPage — Notifications", () => {
  let target: HTMLDivElement;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      if (url === "/api/auth/oidc/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false, provider_name: "", issuer: "", client_id: "", client_secret: "", default_role: "normal", scopes: ["openid", "profile", "email"] }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders current settings and reflects the enabled toggle", () => {
    const store = makeStore();
    const comp = mount(SettingsPage, { target, props: { store, authStore: makeAuthStore() } });
    flushSync();

    const heading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Notifications");
    expect(heading).toBeDefined();
    expect((target.querySelector(".notif-enable-toggle") as HTMLInputElement).checked).toBe(true);

    unmount(comp);
  });

  it("hides push fields until 'Send a daily digest' is checked", () => {
    const store = makeStore();
    const comp = mount(SettingsPage, { target, props: { store, authStore: makeAuthStore() } });
    flushSync();

    const labels = Array.from(target.querySelectorAll(".modal-label")).map((el) => el.textContent);
    expect(labels).not.toContain("HA notify service");

    unmount(comp);
  });

  it("saves edited settings via store.updateNotificationSettings", async () => {
    const store = makeStore();
    const comp = mount(SettingsPage, { target, props: { store, authStore: makeAuthStore() } });
    flushSync();

    const enableToggle = target.querySelector(".notif-enable-toggle") as HTMLInputElement;
    enableToggle.click();
    enableToggle.click(); // leave enabled=true, but confirms the checkbox is wired to the draft
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Save"))!;
    (saveBtn as HTMLButtonElement).click();
    await Promise.resolve();

    expect(store.updateNotificationSettings).toHaveBeenCalledWith(
      expect.objectContaining({ enabled: true, warrantyDaysThreshold: 30 }),
    );

    unmount(comp);
  });
});
