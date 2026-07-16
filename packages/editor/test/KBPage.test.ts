import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBPage from "../src/lib/components/KBPage.svelte";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

const HOME = "home-1";

afterEach(() => vi.unstubAllGlobals());

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "How to paint", content: "# Painting", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], parentId: null, icon: "📄", order: 0,
    ...overrides,
  };
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

// A minimal in-memory fake of the Task 2 backend. Several KBPage flows
// (create-child-then-append-link, cascade delete, restore, reorder) mutate
// state across multiple fetch calls within a single interaction, so a
// stateless canned response can't exercise them -- this fake mirrors just
// enough of routes/kb.py's behavior (soft delete + cascade, next-order
// append, restore) to make those flows observable in a component test.
function createFakeKbBackend(initial: KBEntry[]) {
  let entries: KBEntry[] = initial.map((e) => ({ ...e }));
  let nextId = 100;

  function live(): KBEntry[] { return entries.filter((e) => !e.deletedAt); }
  function trashed(): KBEntry[] { return entries.filter((e) => e.deletedAt); }

  function descendantIds(id: string): string[] {
    const result: string[] = [];
    const stack = [id];
    while (stack.length) {
      const current = stack.pop() as string;
      for (const e of entries) {
        if (e.parentId === current) { result.push(e.id); stack.push(e.id); }
      }
    }
    return result;
  }

  async function handle(url: string, init?: RequestInit) {
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(init.body as string) : undefined;

    if (url.endsWith("/kb") && method === "GET") {
      return { ok: true, status: 200, json: async () => ({ version: 1, entries: live() }) };
    }
    if (url.endsWith("/kb") && method === "POST") {
      const parentId = body.parentId ?? null;
      const siblings = live().filter((e) => e.parentId === parentId);
      const order = siblings.length ? Math.max(...siblings.map((s) => s.order)) + 1 : 0;
      const entry: KBEntry = {
        id: `new-${nextId++}`, title: body.title, content: body.content ?? "",
        createdAt: "2026-07-16T00:00:00Z", updatedAt: "2026-07-16T00:00:00Z",
        attachments: [], parentId, icon: body.icon ?? "📄", order,
      };
      entries.push(entry);
      return { ok: true, status: 201, json: async () => entry };
    }
    if (url.endsWith("/kb/trash") && method === "GET") {
      return { ok: true, status: 200, json: async () => ({ entries: trashed() }) };
    }
    if (url.endsWith("/trash/empty") && method === "POST") {
      const ids = trashed().map((e) => e.id);
      entries = live();
      return { ok: true, status: 200, json: async () => ({ deletedCount: ids.length }) };
    }
    const restoreMatch = url.match(/\/kb\/trash\/([^/]+)\/restore$/);
    if (restoreMatch && method === "POST") {
      const ids = new Set([restoreMatch[1], ...descendantIds(restoreMatch[1])]);
      let count = 0;
      for (const e of entries) if (ids.has(e.id) && e.deletedAt) { e.deletedAt = null; count += 1; }
      return { ok: true, status: 200, json: async () => ({ restoredCount: count }) };
    }
    const permDeleteMatch = url.match(/\/kb\/trash\/([^/]+)$/);
    if (permDeleteMatch && method === "DELETE") {
      entries = entries.filter((e) => e.id !== permDeleteMatch[1]);
      return { ok: true, status: 204, json: async () => null };
    }
    if (url.endsWith("/kb/reorder") && method === "PUT") {
      (body.orderedIds as string[]).forEach((id, index) => {
        const e = entries.find((x) => x.id === id);
        if (e) e.order = index;
      });
      return { ok: true, status: 204, json: async () => null };
    }
    if (method === "PUT") {
      const id = (url.match(/\/kb\/([^/]+)$/) as RegExpMatchArray)[1];
      const e = entries.find((x) => x.id === id);
      if (e) {
        if (body.title !== undefined) e.title = body.title;
        if (body.content !== undefined) e.content = body.content;
        if (body.icon !== undefined) e.icon = body.icon;
        if ("parentId" in body) e.parentId = body.parentId;
      }
      return { ok: true, status: 204, json: async () => null };
    }
    if (method === "DELETE") {
      const id = (url.match(/\/kb\/([^/]+)$/) as RegExpMatchArray)[1];
      const ids = new Set([id, ...descendantIds(id)]);
      let count = 0;
      for (const e of entries) if (ids.has(e.id) && !e.deletedAt) { e.deletedAt = "2026-07-16T00:00:00Z"; count += 1; }
      return { ok: true, status: 200, json: async () => ({ deletedCount: count }) };
    }
    return { ok: true, status: 200, json: async () => ({ version: 1, entries: live() }) };
  }

  return { handle };
}

async function setup(initialEntries: KBEntry[] = [], props: Record<string, unknown> = {}) {
  const backend = createFakeKbBackend(initialEntries);
  vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => backend.handle(url, init)));
  const store = createKBStore(() => HOME);
  await tick();
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(KBPage, { target, props: { store, ...props } });
  flushSync();
  await tick();
  flushSync();
  return { target, comp, store };
}

describe("KBPage — empty state", () => {
  it("shows an empty-content placeholder when nothing is selected", async () => {
    const { target, comp } = await setup([]);
    expect(target.textContent).toContain("Select a page or create one");
    unmount(comp); target.remove();
  });

  it("toolbar has a single New Page button (no separate Folder button)", async () => {
    const { target, comp } = await setup([]);
    const buttons = Array.from(target.querySelectorAll("button")).map((b) => b.textContent?.trim());
    expect(buttons).toContain("＋ New Page");
    expect(buttons).not.toContain("＋ Folder");
    unmount(comp); target.remove();
  });
});

describe("KBPage — selection and deep links", () => {
  it("selects the page named by selectedItemId on mount", async () => {
    const { target, comp } = await setup([makeEntry()], { selectedItemId: "e1" });
    expect(target.querySelector(".content-title")?.textContent).toBe("How to paint");
    unmount(comp); target.remove();
  });

  it("calls onnavigate with the new page id when a tree row is clicked", async () => {
    const onnavigate = vi.fn();
    const entries = [makeEntry(), makeEntry({ id: "e2", title: "Second page", order: 1 })];
    const { target, comp } = await setup(entries, { onnavigate });
    const rows = target.querySelectorAll(".tree-row");
    (rows[1] as HTMLElement).click();
    expect(onnavigate).toHaveBeenCalledWith("e2");
    unmount(comp); target.remove();
  });
});

describe("KBPage — child page creation", () => {
  it("clicking add-child on a tree row creates and selects a child page", async () => {
    const entries = [makeEntry()];
    const { target, comp, store } = await setup(entries);
    (target.querySelector(".add-child") as HTMLElement).click();
    await tick(); flushSync(); await tick(); flushSync();
    const created = store.entries.find((e) => e.parentId === "e1");
    expect(created).toBeDefined();
    expect(target.querySelector(".title-input")).not.toBeNull();
    unmount(comp); target.remove();
  });
});

describe("KBPage — delete with cascade confirmation", () => {
  it("shows the sub-page count in the delete confirmation for a page with children", async () => {
    const entries = [makeEntry(), makeEntry({ id: "e2", title: "Child", parentId: "e1", order: 0 })];
    const { target, comp } = await setup(entries, { selectedItemId: "e1" });
    (target.querySelector('[title="Delete page"]') as HTMLElement).click();
    flushSync();
    expect(target.textContent).toContain("sub-page");
    unmount(comp); target.remove();
  });

  it("clears selection after confirming delete of the selected page", async () => {
    const entries = [makeEntry()];
    const { target, comp } = await setup(entries, { selectedItemId: "e1" });
    (target.querySelector('[title="Delete page"]') as HTMLElement).click();
    flushSync();
    const confirmBtn = Array.from(target.querySelectorAll(".header-actions button")).find((b) => b.textContent === "✓") as HTMLElement;
    confirmBtn.click();
    await tick(); flushSync(); await tick(); flushSync();
    expect(target.textContent).toContain("Select a page or create one");
    unmount(comp); target.remove();
  });
});

describe("KBPage — trash", () => {
  it("clicking the Trash link switches the content pane to the trash view", async () => {
    const { target, comp } = await setup([]);
    const trashLink = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Trash")) as HTMLElement;
    trashLink.click();
    await tick(); flushSync();
    expect(target.textContent).toContain("Trash is empty.");
    unmount(comp); target.remove();
  });
});
