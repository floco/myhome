export interface AuthUser {
  id: string;
  username: string;
  role: "admin" | "normal" | "ro";
}

export function createAuthStore() {
  let user = $state<AuthUser | null>(null);
  let checking = $state(true);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/auth/me");
      user = resp.ok ? await resp.json() : null;
    } catch {
      user = null;
    } finally {
      checking = false;
    }
  }

  async function login(username: string, password: string): Promise<AuthUser> {
    const resp = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) throw new Error("Invalid credentials");
    const u: AuthUser = await resp.json();
    user = u;
    return u;
  }

  async function logout(): Promise<void> {
    await fetch("/api/auth/logout", { method: "POST" });
    user = null;
  }

  async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const resp = await fetch("/api/auth/me/password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (!resp.ok) {
      const data: { detail?: string } = await resp.json().catch(() => ({}));
      throw new Error(data.detail ?? `HTTP ${resp.status}`);
    }
  }

  init();

  return {
    get user() { return user; },
    get checking() { return checking; },
    login,
    logout,
    changePassword,
  };
}
