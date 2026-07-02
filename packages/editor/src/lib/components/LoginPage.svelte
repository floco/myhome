<script lang="ts">
  interface Props {
    onlogin: () => void;
    login: (username: string, password: string) => Promise<unknown>;
  }
  let { onlogin, login }: Props = $props();

  let username = $state("");
  let password = $state("");
  let error = $state<string | null>(null);
  let loading = $state(false);

  async function handleSubmit(e: SubmitEvent): Promise<void> {
    e.preventDefault();
    error = null;
    loading = true;
    try {
      await login(username, password);
      onlogin();
    } catch {
      error = "Invalid username or password";
    } finally {
      loading = false;
    }
  }
</script>

<div class="login-page">
  <div class="login-card">
    <div class="login-header">
      <span class="login-logo">🏠</span>
      <h1 class="login-title">MyHome</h1>
      <p class="login-subtitle">Sign in to continue</p>
    </div>

    <form class="login-form" onsubmit={handleSubmit}>
      <div class="form-field">
        <label for="login-username">Username</label>
        <input
          id="login-username"
          type="text"
          bind:value={username}
          autocomplete="username"
          required
        />
      </div>
      <div class="form-field">
        <label for="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          bind:value={password}
          autocomplete="current-password"
          required
        />
      </div>

      {#if error}
        <div class="login-error">{error}</div>
      {/if}

      <button type="submit" class="login-btn" disabled={loading}>
        {loading ? "Signing in…" : "Sign in"}
      </button>
    </form>

    <p class="login-footer">Contact your admin to create an account</p>
  </div>
</div>

<style>
  .login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
  }

  .login-card {
    width: 400px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 40px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .login-header {
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .login-logo { font-size: 2rem; }

  .login-title {
    margin: 0;
    font-size: 1.5rem;
    color: var(--text);
    font-family: var(--font-sans);
  }

  .login-subtitle {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .login-form { display: flex; flex-direction: column; gap: 16px; }

  .form-field { display: flex; flex-direction: column; gap: 6px; }

  .form-field label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-family: var(--font-sans);
  }

  .form-field input {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.9rem;
    color: var(--text);
    font-family: var(--font-sans);
  }

  .form-field input:focus {
    outline: none;
    border-color: var(--accent);
  }

  .login-error {
    background: color-mix(in srgb, red 10%, transparent);
    border: 1px solid color-mix(in srgb, red 30%, transparent);
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: var(--text);
  }

  .login-btn {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 12px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    font-family: var(--font-sans);
  }

  .login-btn:disabled { opacity: 0.6; cursor: not-allowed; }

  .login-footer {
    margin: 0;
    text-align: center;
    font-size: 0.78rem;
    color: var(--text-faint);
  }
</style>
