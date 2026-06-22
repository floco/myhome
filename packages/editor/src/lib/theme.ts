/** Persisted theme preference, matching the values theme.css's [data-theme] selector understands. */
export type Theme = "light" | "dark";

const STORAGE_KEY = "myhome-theme";

/** Reads the persisted theme from localStorage, defaulting to "light" if unset or invalid. */
export function getStoredTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "dark" ? "dark" : "light";
}

/** Sets the data-theme attribute on <html>, activating the matching CSS custom properties. */
export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

/** Persists the theme to localStorage and applies it immediately. */
export function setTheme(theme: Theme): void {
  localStorage.setItem(STORAGE_KEY, theme);
  applyTheme(theme);
}

/** Applies the persisted (or default) theme on startup and returns it. */
export function initTheme(): Theme {
  const theme = getStoredTheme();
  applyTheme(theme);
  return theme;
}

/** Flips the given theme, persists it, and applies it. Takes the current value rather than
 *  reading storage itself, since callers (e.g. a topbar toggle button) already hold it in state. */
export function toggleTheme(current: Theme): Theme {
  const next: Theme = current === "light" ? "dark" : "light";
  setTheme(next);
  return next;
}
