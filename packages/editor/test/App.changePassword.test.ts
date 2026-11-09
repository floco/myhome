import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (url === "/api/auth/me") {
      return Promise.resolve({ ok: true, status: 200, statusText: "OK", json: async () => ({ id: "u1", username: "admin", role: "admin" }) });
    }
    return Promise.resolve({ ok: false, status: 404, statusText: "Not Found", json: async () => undefined });
  }));
}

describe("App — change password", () => {
  let app: ReturnType<typeof mount> | undefined;
  let target: HTMLElement;

  afterEach(() => {
    if (app) unmount(app);
    app = undefined;
    target?.remove();
    vi.unstubAllGlobals();
  });

  it("opens a labelled change-password dialog from the user menu", async () => {
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    window.location.hash = "#/plan";
    app = mount(App, { target });
    await tick(); await tick(); await tick();
    flushSync();

    (target.querySelector("button.user-chip") as HTMLButtonElement).click();
    flushSync();
    const item = [...target.querySelectorAll(".user-dropdown-item")].find((b) => b.textContent?.includes("Change password")) as HTMLButtonElement;
    item.click();
    flushSync();

    const dialog = target.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    const labels = [...dialog!.querySelectorAll("label")].map((l) => l.textContent?.trim());
    expect(labels).toHaveLength(2);
    expect(dialog!.querySelectorAll('label input[type="password"]')).toHaveLength(2);
  });
});
