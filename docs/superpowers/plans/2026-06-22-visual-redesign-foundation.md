# Visual Redesign — Foundation (Spec 6, Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce the design token system (light/dark CSS variables), a theme toggle with persistence, and a shared UI component library (`Button`, `Card`, `Panel`, `Input`, `Badge`, `StatTile`, `Modal`), then apply it to the app's global chrome (topbar in `App.svelte`, nav in `NavMenu.svelte`).

**Architecture:** Pure frontend, styling-only. A new `theme.css` defines CSS custom properties on `:root` (light, default) and `[data-theme="dark"]`. A new `theme.ts` reads/writes the active theme to `localStorage` and sets the `data-theme` attribute on `<html>`. New Svelte components live in `packages/editor/src/lib/components/ui/` and consume the tokens. No backend, data model, or store changes — see `docs/superpowers/specs/2026-06-22-visual-redesign-design.md` for full context. This is Phase 1 of 5; later phases (editor panels/canvas, modals, pages, overlays) build on the components and tokens this plan creates.

**Tech Stack:** Svelte 5 (runes/snippets), TypeScript, Vitest + jsdom for tests, no new dependencies.

---

### Task 1: Design token stylesheet

**Files:**
- Create: `packages/editor/src/lib/theme.css`

- [ ] **Step 1: Write the tokens file**

```css
/* packages/editor/src/lib/theme.css */

:root {
  /* Surfaces & text — light (default) */
  --bg: #f5f5f7;
  --surface: #ffffff;
  --surface-alt: #fafafa;
  --surface-hover: #f0f0f2;
  --border: #e5e5e7;
  --text: #1a1a1e;
  --text-muted: #767680;
  --text-faint: #9a9aa2;
  --accent: #111111;
  --accent-contrast: #ffffff;

  /* Semantic */
  --success: #2a8f5c;
  --danger: #e0444d;
  --warning: #d99a1b;

  /* Scales (theme-independent) */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-pill: 999px;

  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.16);

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;

  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;

  /* Floor-plan canvas (tuned separately from UI chrome; consumed in Phase 2) */
  --canvas-bg: #eceef1;
  --canvas-grid: #d8dadf;
  --canvas-wall: #2a2a30;
  --canvas-wall-selected: #111111;
  --canvas-room-fill: #ffffff;
}

[data-theme="dark"] {
  --bg: #15151a;
  --surface: #1e1e24;
  --surface-alt: #242430;
  --surface-hover: #2a2a33;
  --border: #2c2c35;
  --text: #e8e8ea;
  --text-muted: #9a9aa5;
  --text-faint: #6b6b75;
  --accent: #f0f0f0;
  --accent-contrast: #111111;

  --success: #4ade80;
  --danger: #f87171;
  --warning: #fbbf24;

  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.45);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);

  --canvas-bg: #1c1c22;
  --canvas-grid: #2a2a32;
  --canvas-wall: #d8d8dc;
  --canvas-wall-selected: #ffffff;
  --canvas-room-fill: #232328;
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/editor/src/lib/theme.css
git commit -m "feat(theme): add light/dark design token stylesheet"
```

---

### Task 2: Theme persistence module

**Files:**
- Create: `packages/editor/src/lib/theme.ts`
- Test: `packages/editor/test/theme.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/theme.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { getStoredTheme, applyTheme, setTheme, initTheme, toggleTheme } from "../src/lib/theme";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("theme", () => {
  it("defaults to light when nothing is stored", () => {
    expect(getStoredTheme()).toBe("light");
  });

  it("returns the stored theme when present", () => {
    localStorage.setItem("myhome-theme", "dark");
    expect(getStoredTheme()).toBe("dark");
  });

  it("applyTheme sets the data-theme attribute on the html element", () => {
    applyTheme("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("setTheme persists to localStorage and applies the attribute", () => {
    setTheme("dark");
    expect(localStorage.getItem("myhome-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("initTheme applies and returns the stored theme", () => {
    localStorage.setItem("myhome-theme", "dark");
    expect(initTheme()).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("initTheme defaults to light and applies it when nothing stored", () => {
    expect(initTheme()).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggleTheme flips light to dark and persists it", () => {
    expect(toggleTheme("light")).toBe("dark");
    expect(localStorage.getItem("myhome-theme")).toBe("dark");
  });

  it("toggleTheme flips dark to light and persists it", () => {
    expect(toggleTheme("dark")).toBe("light");
    expect(localStorage.getItem("myhome-theme")).toBe("light");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- theme.test.ts`
Expected: FAIL — `Failed to resolve import "../src/lib/theme"` (module does not exist yet)

- [ ] **Step 3: Write the implementation**

```typescript
// packages/editor/src/lib/theme.ts
export type Theme = "light" | "dark";

const STORAGE_KEY = "myhome-theme";

export function getStoredTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "dark" ? "dark" : "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(STORAGE_KEY, theme);
  applyTheme(theme);
}

export function initTheme(): Theme {
  const theme = getStoredTheme();
  applyTheme(theme);
  return theme;
}

export function toggleTheme(current: Theme): Theme {
  const next: Theme = current === "light" ? "dark" : "light";
  setTheme(next);
  return next;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- theme.test.ts`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/theme.ts packages/editor/test/theme.test.ts
git commit -m "feat(theme): add theme persistence module with tests"
```

---

### Task 3: Wire the theme system into the app shell

**Files:**
- Modify: `packages/editor/src/main.ts`

- [ ] **Step 1: Import the tokens and initialize the theme before mount**

```typescript
// packages/editor/src/main.ts
import "./lib/theme.css";
import { initTheme } from "./lib/theme";
import { mount } from "svelte";
import App from "./App.svelte";

initTheme();

const target = document.getElementById("app");
if (!target) throw new Error("Missing #app element");

const app = mount(App, { target });

export default app;
```

- [ ] **Step 2: Run the full test suite to confirm nothing broke**

Run: `npm test -w packages/editor`
Expected: PASS (all existing tests still pass — `main.ts` is not covered by tests, this just confirms no collateral breakage)

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/main.ts
git commit -m "feat(theme): initialize theme and load tokens on app startup"
```

---

### Task 4: `ui/Button.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/Button.svelte`
- Test: `packages/editor/test/Button.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/Button.test.ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import Button from "../src/lib/components/ui/Button.svelte";

describe("ui/Button", () => {
  it("defaults to the primary variant", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Button, { target, props: {} });

    const btn = target.querySelector("button")!;
    expect(btn.classList.contains("ui-button-primary")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("applies the requested variant class", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Button, { target, props: { variant: "secondary" } });

    const btn = target.querySelector("button")!;
    expect(btn.classList.contains("ui-button-secondary")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("calls onclick when clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclick = vi.fn();
    const comp = mount(Button, { target, props: { onclick } });

    target.querySelector("button")!.click();
    expect(onclick).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("does not call onclick when disabled", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclick = vi.fn();
    const comp = mount(Button, { target, props: { onclick, disabled: true } });

    const btn = target.querySelector("button")!;
    expect(btn.disabled).toBe(true);
    btn.click();
    expect(onclick).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- Button.test.ts`
Expected: FAIL — module `../src/lib/components/ui/Button.svelte` not found

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/ui/Button.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "primary" | "secondary" | "ghost";
    onclick?: () => void;
    disabled?: boolean;
    title?: string;
    children?: Snippet;
  }
  let { variant = "primary", onclick, disabled = false, title, children }: Props = $props();
</script>

<button class="ui-button ui-button-{variant}" {disabled} {title} {onclick}>
  {@render children?.()}
</button>

<style>
  .ui-button {
    font-family: var(--font-sans);
    font-size: 12px; font-weight: 600;
    border: none; border-radius: var(--radius-pill);
    padding: 8px 18px; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  }
  .ui-button:disabled { opacity: 0.5; cursor: default; }

  .ui-button-primary { background: var(--accent); color: var(--accent-contrast); }
  .ui-button-primary:hover:not(:disabled) { opacity: 0.85; }

  .ui-button-secondary {
    background: var(--surface); color: var(--text);
    border: 1px solid var(--border);
  }
  .ui-button-secondary:hover:not(:disabled) { background: var(--surface-hover); }

  .ui-button-ghost { background: transparent; color: var(--text-muted); }
  .ui-button-ghost:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- Button.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Button.svelte packages/editor/test/Button.test.ts
git commit -m "feat(ui): add shared Button component"
```

---

### Task 5: `ui/Card.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/Card.svelte`
- Test: `packages/editor/test/Card.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/Card.test.ts
import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Card from "../src/lib/components/ui/Card.svelte";

describe("ui/Card", () => {
  it("renders a ui-card container", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Card, { target, props: {} });

    expect(target.querySelector(".ui-card")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- Card.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/ui/Card.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    children?: Snippet;
  }
  let { children }: Props = $props();
</script>

<div class="ui-card">
  {@render children?.()}
</div>

<style>
  .ui-card {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-4);
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- Card.test.ts`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Card.svelte packages/editor/test/Card.test.ts
git commit -m "feat(ui): add shared Card component"
```

---

### Task 6: `ui/Panel.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/Panel.svelte`
- Test: `packages/editor/test/Panel.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/Panel.test.ts
import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Panel from "../src/lib/components/ui/Panel.svelte";

describe("ui/Panel", () => {
  it("defaults to normal density", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Panel, { target, props: {} });

    expect(target.querySelector(".ui-panel-normal")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("applies compact density when requested", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Panel, { target, props: { density: "compact" } });

    expect(target.querySelector(".ui-panel-compact")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- Panel.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/ui/Panel.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    density?: "normal" | "compact";
    children?: Snippet;
  }
  let { density = "normal", children }: Props = $props();
</script>

<div class="ui-panel ui-panel-{density}">
  {@render children?.()}
</div>

<style>
  .ui-panel {
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .ui-panel-normal { border-radius: var(--radius-lg); padding: var(--space-4); }
  .ui-panel-compact { border-radius: var(--radius-sm); padding: var(--space-2); font-size: 12px; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- Panel.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Panel.svelte packages/editor/test/Panel.test.ts
git commit -m "feat(ui): add shared Panel component with density variants"
```

---

### Task 7: `ui/Input.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/Input.svelte`
- Test: `packages/editor/test/Input.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/Input.test.ts
import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Input from "../src/lib/components/ui/Input.svelte";

describe("ui/Input", () => {
  it("renders the given value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: { value: "Garden Hose" } });

    const input = target.querySelector("input")!;
    expect(input.value).toBe("Garden Hose");

    unmount(comp);
    target.remove();
  });

  it("renders the placeholder when no value is set", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: { placeholder: "Search…" } });

    const input = target.querySelector("input")!;
    expect(input.placeholder).toBe("Search…");
    expect(input.value).toBe("");

    unmount(comp);
    target.remove();
  });

  it("applies the ui-input class", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: {} });

    expect(target.querySelector("input.ui-input")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- Input.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/ui/Input.svelte -->
<script lang="ts">
  interface Props {
    value?: string;
    placeholder?: string;
    type?: string;
  }
  let { value = $bindable(""), placeholder = "", type = "text" }: Props = $props();
</script>

<input class="ui-input" {type} {placeholder} bind:value />

<style>
  .ui-input {
    font-family: var(--font-sans);
    font-size: 13px;
    background: var(--surface-alt);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 8px 12px;
    width: 100%;
    box-sizing: border-box;
  }
  .ui-input:focus { outline: none; border-color: var(--accent); }
  .ui-input::placeholder { color: var(--text-faint); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- Input.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Input.svelte packages/editor/test/Input.test.ts
git commit -m "feat(ui): add shared Input component"
```

---

### Task 8: `ui/Badge.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/Badge.svelte`
- Test: `packages/editor/test/Badge.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/Badge.test.ts
import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Badge from "../src/lib/components/ui/Badge.svelte";

describe("ui/Badge", () => {
  it("renders the label text", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Badge, { target, props: { label: "Done", variant: "success" } });

    expect(target.querySelector(".ui-badge")!.textContent).toBe("Done");

    unmount(comp);
    target.remove();
  });

  it("applies the variant class", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Badge, { target, props: { label: "Overdue", variant: "danger" } });

    expect(target.querySelector(".ui-badge-danger")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("defaults to the neutral variant", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Badge, { target, props: { label: "Planned" } });

    expect(target.querySelector(".ui-badge-neutral")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- Badge.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/ui/Badge.svelte -->
<script lang="ts">
  interface Props {
    label: string;
    variant?: "success" | "danger" | "warning" | "neutral";
  }
  let { label, variant = "neutral" }: Props = $props();
</script>

<span class="ui-badge ui-badge-{variant}">{label}</span>

<style>
  .ui-badge {
    font-family: var(--font-sans);
    font-size: 11px; font-weight: 600;
    border-radius: var(--radius-pill);
    padding: 3px 10px;
    white-space: nowrap;
  }
  .ui-badge-neutral { background: var(--surface-alt); color: var(--text-muted); }
  .ui-badge-success { background: color-mix(in srgb, var(--success) 18%, var(--surface)); color: var(--success); }
  .ui-badge-danger { background: color-mix(in srgb, var(--danger) 18%, var(--surface)); color: var(--danger); }
  .ui-badge-warning { background: color-mix(in srgb, var(--warning) 18%, var(--surface)); color: var(--warning); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- Badge.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Badge.svelte packages/editor/test/Badge.test.ts
git commit -m "feat(ui): add shared Badge component"
```

---

### Task 9: `ui/StatTile.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/StatTile.svelte`
- Test: `packages/editor/test/StatTile.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/StatTile.test.ts
import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import StatTile from "../src/lib/components/ui/StatTile.svelte";

describe("ui/StatTile", () => {
  it("renders the value and label", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 128, label: "Items" } });

    expect(target.querySelector(".ui-stat-value")!.textContent).toBe("128");
    expect(target.querySelector(".ui-stat-label")!.textContent).toBe("Items");

    unmount(comp);
    target.remove();
  });

  it("accepts a string value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: "18.6k km", label: "Distance" } });

    expect(target.querySelector(".ui-stat-value")!.textContent).toBe("18.6k km");

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- StatTile.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/ui/StatTile.svelte -->
<script lang="ts">
  interface Props {
    value: string | number;
    label: string;
  }
  let { value, label }: Props = $props();
</script>

<div class="ui-card ui-stat-tile">
  <div class="ui-stat-value">{value}</div>
  <div class="ui-stat-label">{label}</div>
</div>

<style>
  .ui-stat-tile {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-3);
  }
  .ui-stat-value { font-size: 22px; font-weight: 700; color: var(--text); line-height: 1.2; }
  .ui-stat-label {
    font-size: 10px; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: 0.05em;
    margin-top: 2px;
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- StatTile.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/StatTile.svelte packages/editor/test/StatTile.test.ts
git commit -m "feat(ui): add shared StatTile component"
```

---

### Task 10: `ui/Modal.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/ui/Modal.svelte`
- Test: `packages/editor/test/Modal.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/editor/test/Modal.test.ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import Modal from "../src/lib/components/ui/Modal.svelte";

describe("ui/Modal", () => {
  it("renders nothing when closed", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Modal, { target, props: { open: false, title: "Edit item", onclose: vi.fn() } });

    expect(target.querySelector(".ui-modal")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("renders the dialog and title when open", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Modal, { target, props: { open: true, title: "Edit item", onclose: vi.fn() } });

    const dialog = target.querySelector(".ui-modal")!;
    expect(dialog).not.toBeNull();
    expect(dialog.querySelector(".ui-modal-title")!.textContent).toBe("Edit item");

    unmount(comp);
    target.remove();
  });

  it("calls onclose when the backdrop is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclose = vi.fn();
    const comp = mount(Modal, { target, props: { open: true, title: "Edit item", onclose } });

    (target.querySelector(".ui-modal-backdrop") as HTMLElement).click();
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("calls onclose when the close button is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclose = vi.fn();
    const comp = mount(Modal, { target, props: { open: true, title: "Edit item", onclose } });

    (target.querySelector(".ui-modal-close") as HTMLElement).click();
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w packages/editor -- Modal.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```svelte
<!-- packages/editor/src/lib/components/ui/Modal.svelte -->
<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    open: boolean;
    title: string;
    onclose: () => void;
    children?: Snippet;
    footer?: Snippet;
  }
  let { open, title, onclose, children, footer }: Props = $props();
</script>

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="ui-modal-backdrop" role="presentation" onclick={onclose}></div>
  <div class="ui-modal" role="dialog" aria-label={title}>
    <div class="ui-modal-header">
      <h2 class="ui-modal-title">{title}</h2>
      <button class="ui-modal-close" onclick={onclose} aria-label="Close">✕</button>
    </div>
    <div class="ui-modal-body">
      {@render children?.()}
    </div>
    {#if footer}
      <div class="ui-modal-footer">
        {@render footer()}
      </div>
    {/if}
  </div>
{/if}

<style>
  .ui-modal-backdrop {
    position: fixed; inset: 0; z-index: 99;
    background: rgba(0, 0, 0, 0.45);
  }
  .ui-modal {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
    z-index: 100;
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    width: 480px; max-width: 90vw; max-height: 90vh;
    display: flex; flex-direction: column;
    overflow: hidden;
  }
  .ui-modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--space-4);
    border-bottom: 1px solid var(--border);
  }
  .ui-modal-title { font-size: 16px; font-weight: 600; color: var(--text); margin: 0; }
  .ui-modal-close {
    border: none; background: transparent; color: var(--text-muted);
    font-size: 14px; cursor: pointer; width: 28px; height: 28px;
    border-radius: var(--radius-sm);
  }
  .ui-modal-close:hover { background: var(--surface-hover); color: var(--text); }
  .ui-modal-body { padding: var(--space-4); overflow-y: auto; flex: 1; }
  .ui-modal-footer {
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--border);
    display: flex; justify-content: flex-end; gap: var(--space-2);
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w packages/editor -- Modal.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Modal.svelte packages/editor/test/Modal.test.ts
git commit -m "feat(ui): add shared Modal component"
```

---

### Task 11: Re-skin the topbar in `App.svelte`

**Files:**
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Add the theme toggle button next to the app title**

Find this block (around line 467):

```svelte
    <span class="app-title">myhome</span>

    {#if isFloorPlan}
```

Replace with:

```svelte
    <span class="app-title">myhome</span>

    <button
      class="icon-btn theme-toggle"
      title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
      onclick={handleToggleTheme}
    >{theme === "light" ? "🌙" : "☀️"}</button>

    {#if isFloorPlan}
```

- [ ] **Step 2: Add theme state and the toggle handler to the script block**

Find the store declarations (around line 50):

```typescript
  const worksStore = createWorksStore();
```

Add directly after it:

```typescript
  const worksStore = createWorksStore();

  let theme = $state<Theme>(getStoredTheme());
  function handleToggleTheme(): void {
    theme = toggleTheme(theme);
  }
```

Add the import at the top of the script block, alongside the other `./lib/...` imports:

```typescript
  import { getStoredTheme, toggleTheme, type Theme } from "./lib/theme";
```

- [ ] **Step 3: Replace hardcoded topbar colors with tokens**

Find the `<style>` block (around line 896) and replace these rules:

```css
  .app {
    display: flex; flex-direction: column;
    height: 100vh; font-family: sans-serif;
    background: #1a1a2e;
  }

  .topbar {
    height: 36px;
    background: #1e1e2e; color: #ccc;
    display: flex; align-items: center;
    padding: 0 8px; gap: 8px;
    flex-shrink: 0;
    border-bottom: 1px solid #2a2a3a;
  }

  .hamburger {
    width: 32px; height: 32px; flex-shrink: 0;
    border: none; background: transparent; color: #999;
    font-size: 16px; cursor: pointer; border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
  }
  .hamburger:hover { background: #2a2a4a; color: #eee; }

  .app-title {
    font-size: 14px; font-weight: 600; color: #eee;
    margin-right: 8px; flex-shrink: 0;
  }

  .topbar-sep {
    width: 1px; height: 18px; background: #333; flex-shrink: 0; margin: 0 4px;
  }
  .spacer { flex: 1; }

  .toolbar {
    display: flex; align-items: center; gap: 2px; flex-shrink: 0;
  }
  .toolbar .sep {
    width: 1px; height: 16px; background: #333; margin: 0 3px; flex-shrink: 0;
  }
  .toolbar button {
    width: 28px; height: 28px;
    border: none; border-radius: 4px; background: transparent;
    color: #999; cursor: pointer; font-size: 14px;
    display: flex; align-items: center; justify-content: center; padding: 0;
  }
  .toolbar button:hover:not(:disabled) { background: #2a2a4a; color: #eee; }
  .toolbar button.active { background: #2a2a5a; color: #aaf; }
  .toolbar button.delete { color: #c66; }
  .toolbar button.delete:hover:not(:disabled) { background: #422; color: #f88; }
  .toolbar button:disabled { opacity: 0.35; cursor: default; }

  .icon-btn {
    width: 30px; height: 30px;
    border: none; border-radius: 4px; background: transparent;
    color: #999; cursor: pointer; font-size: 15px;
    display: flex; align-items: center; justify-content: center; padding: 0;
    flex-shrink: 0; text-decoration: none;
  }
  .icon-btn:hover:not(:disabled) { background: #2a2a4a; color: #eee; }
  .icon-btn.active { background: #2a2a5a; color: #aaf; }
  .icon-btn.save-btn { color: #4c9; }
  .icon-btn.save-btn:hover:not(:disabled) { background: #1a3a2a; color: #6eb; }
  .icon-btn.save-btn.saved { color: #2a6; }
  .icon-btn.save-btn.save-error { color: #f44; }
  .icon-btn:disabled { opacity: 0.5; cursor: default; }
  .new-chore-btn { color: #4c9; font-size: 18px; font-weight: 600; }
  .new-chore-btn:hover { background: #1a3a2a; color: #6eb; }
```

with:

```css
  .app {
    display: flex; flex-direction: column;
    height: 100vh; font-family: var(--font-sans);
    background: var(--bg);
  }

  .topbar {
    height: 48px;
    background: var(--surface); color: var(--text);
    display: flex; align-items: center;
    padding: 0 var(--space-3); gap: var(--space-2);
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
  }

  .hamburger {
    width: 32px; height: 32px; flex-shrink: 0;
    border: none; background: transparent; color: var(--text-muted);
    font-size: 16px; cursor: pointer; border-radius: var(--radius-sm);
    display: flex; align-items: center; justify-content: center;
  }
  .hamburger:hover { background: var(--surface-hover); color: var(--text); }

  .app-title {
    font-size: 14px; font-weight: 600; color: var(--text);
    margin-right: var(--space-2); flex-shrink: 0;
  }

  .theme-toggle { margin-right: var(--space-2); }

  .topbar-sep {
    width: 1px; height: 18px; background: var(--border); flex-shrink: 0; margin: 0 4px;
  }
  .spacer { flex: 1; }

  .toolbar {
    display: flex; align-items: center; gap: 2px; flex-shrink: 0;
  }
  .toolbar .sep {
    width: 1px; height: 16px; background: var(--border); margin: 0 3px; flex-shrink: 0;
  }
  .toolbar button {
    width: 28px; height: 28px;
    border: none; border-radius: var(--radius-sm); background: transparent;
    color: var(--text-muted); cursor: pointer; font-size: 14px;
    display: flex; align-items: center; justify-content: center; padding: 0;
  }
  .toolbar button:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  .toolbar button.active { background: var(--surface-hover); color: var(--accent); }
  .toolbar button.delete { color: var(--danger); }
  .toolbar button.delete:hover:not(:disabled) { background: var(--surface-hover); color: var(--danger); }
  .toolbar button:disabled { opacity: 0.35; cursor: default; }

  .icon-btn {
    width: 30px; height: 30px;
    border: none; border-radius: var(--radius-sm); background: transparent;
    color: var(--text-muted); cursor: pointer; font-size: 15px;
    display: flex; align-items: center; justify-content: center; padding: 0;
    flex-shrink: 0; text-decoration: none;
  }
  .icon-btn:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  .icon-btn.active { background: var(--surface-hover); color: var(--accent); }
  .icon-btn.save-btn { color: var(--success); }
  .icon-btn.save-btn:hover:not(:disabled) { background: var(--surface-hover); }
  .icon-btn.save-btn.saved { color: var(--success); }
  .icon-btn.save-btn.save-error { color: var(--danger); }
  .icon-btn:disabled { opacity: 0.5; cursor: default; }
  .new-chore-btn { color: var(--success); font-size: 18px; font-weight: 600; }
  .new-chore-btn:hover { background: var(--surface-hover); }
```

- [ ] **Step 4: Run the existing App tests**

Run: `npm test -w packages/editor -- App.test.ts`
Expected: PASS — no behavioral change, only colors/tokens and the new toggle button

- [ ] **Step 5: Manually verify in the browser**

Run: `npm run dev -w packages/editor`, open the printed URL, confirm:
- App loads in light theme by default (white topbar, light gray page background)
- Clicking the 🌙 button switches to dark theme (toggle becomes ☀️) and the topbar/page go dark
- Reloading the page keeps the chosen theme (persisted via `localStorage`)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat(theme): re-skin topbar with design tokens and add theme toggle"
```

---

### Task 12: Re-skin `NavMenu.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/NavMenu.svelte`

- [ ] **Step 1: Replace the `<style>` block**

Replace the entire `<style>` block with:

```css
<style>
  .backdrop {
    display: none;
    position: fixed; inset: 0; z-index: 19;
    background: rgba(0, 0, 0, 0.45);
  }
  @media (max-width: 600px) {
    .backdrop { display: block; }
  }

  .nav {
    position: relative; z-index: 20;
    display: flex; flex-direction: column;
    width: 44px; flex-shrink: 0;
    background: var(--surface); border-right: 1px solid var(--border);
    overflow: hidden;
    transition: width 0.18s ease;
  }
  .nav.expanded { width: 180px; }

  .nav-body { flex: 1; display: flex; flex-direction: column; min-width: 180px; padding: 8px 6px 0; gap: 2px; }

  .nav-item {
    display: flex; align-items: center; gap: 10px;
    height: 40px; padding: 0 12px;
    margin: 0 2px;
    color: var(--text-muted); text-decoration: none; white-space: nowrap;
    border-radius: var(--radius-pill);
  }
  .nav-item:hover { background: var(--surface-hover); color: var(--text); }
  .nav-item.active { color: var(--accent-contrast); background: var(--accent); }

  .nav-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; line-height: 1; }
  .nav-label { font-size: 12px; font-weight: 500; }

  .nav-separator { border: none; border-top: 1px solid var(--border); margin: 8px 10px; }

  @media (max-width: 600px) {
    .nav {
      position: fixed;
      top: 48px; bottom: 0; left: 0;
      width: 0;
    }
    .nav.expanded { width: 200px; }
  }
</style>
```

(Only the `<style>` block changes — the `<script>` and markup above it stay as they are.)

- [ ] **Step 2: Run the test suite**

Run: `npm test -w packages/editor`
Expected: PASS — no test directly covers `NavMenu`, so this confirms no collateral breakage elsewhere

- [ ] **Step 3: Manually verify in the browser**

Run: `npm run dev -w packages/editor` (if not already running), open the hamburger menu, confirm:
- The active route shows a solid pill highlight (black background in light mode, near-white in dark mode) instead of the old left-border indicator
- Hover state shows a subtle gray highlight
- Both light and dark themes look correct (toggle via the topbar button added in Task 11)

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/NavMenu.svelte
git commit -m "feat(theme): re-skin NavMenu with pill active state and tokens"
```

---

### Task 13: Full verification pass

- [ ] **Step 1: Run the full test suite**

Run: `npm test -w packages/editor`
Expected: PASS — all tests green, including the 8 new component/theme tests added in this plan (132 previously passing + new ones)

- [ ] **Step 2: Note on typecheck**

Run: `npm run typecheck -w packages/editor`
This command has 8 pre-existing errors on `main` unrelated to this work (missing `.svelte` type declarations, unused variables in test fixtures). Confirm the error count and list of files did not grow compared to the pre-existing baseline — do not attempt to fix unrelated baseline errors as part of this plan.

- [ ] **Step 3: Manual cross-page check**

With `npm run dev -w packages/editor` running, visit each route (`#/`, `#/chores`, `#/inventory`, `#/consumables`, `#/works`, `#/costs`, `#/settings`) in both light and dark mode (toggle in the topbar) and confirm the topbar and nav render correctly and legibly on every page. Pages themselves are not yet restyled (that's Phase 4) — only topbar/nav consistency matters here.

- [ ] **Step 4: Final commit (if any cleanup was needed)**

```bash
git status
```

If the working tree is clean, no commit is needed — all changes were already committed in Tasks 1–12.
