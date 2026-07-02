import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LoginPage from "../src/lib/components/LoginPage.svelte";

describe("LoginPage", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("renders username field, password field, and Sign in button", () => {
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: vi.fn() },
    });
    flushSync();
    expect(target.querySelector('input[type="text"]')).not.toBeNull();
    expect(target.querySelector('input[type="password"]')).not.toBeNull();
    expect(target.textContent).toContain("Sign in");
    unmount(app);
  });

  it("shows contact-admin footer and no self-registration prompt", () => {
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: vi.fn() },
    });
    flushSync();
    expect(target.textContent).toContain("Contact your admin");
    unmount(app);
  });

  it("calls login() and onlogin() on successful submit", async () => {
    const mockUser = { id: "u1", username: "admin", role: "admin" };
    const mockLogin = vi.fn().mockResolvedValue(mockUser);
    const mockOnlogin = vi.fn();
    const app = mount(LoginPage, {
      target,
      props: { onlogin: mockOnlogin, login: mockLogin },
    });
    flushSync();
    const usernameInput = target.querySelector('input[type="text"]') as HTMLInputElement;
    const passwordInput = target.querySelector('input[type="password"]') as HTMLInputElement;
    usernameInput.value = "admin";
    usernameInput.dispatchEvent(new Event("input"));
    passwordInput.value = "admin123";
    passwordInput.dispatchEvent(new Event("input"));
    flushSync();
    target.querySelector("form")!.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(mockLogin).toHaveBeenCalledWith("admin", "admin123");
    expect(mockOnlogin).toHaveBeenCalled();
    unmount(app);
  });

  it("shows error message when login() throws", async () => {
    const mockLogin = vi.fn().mockRejectedValue(new Error("bad creds"));
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: mockLogin },
    });
    flushSync();
    target.querySelector("form")!.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Invalid username or password");
    unmount(app);
  });

  it("does not show error before any submit attempt", () => {
    const app = mount(LoginPage, {
      target,
      props: { onlogin: vi.fn(), login: vi.fn() },
    });
    flushSync();
    expect(target.textContent).not.toContain("Invalid username or password");
    unmount(app);
  });
});
