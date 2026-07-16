import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBTree from "../src/lib/components/ui/KBTree.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "How to paint", content: "", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], parentId: null, icon: "📄", order: 0,
    ...overrides,
  };
}

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    entries: [] as KBEntry[],
    selectedId: null,
    searchQuery: "",
    collapsedIds: new Set<string>(),
    renamingId: null,
    dragging: null,
    onselect: vi.fn(),
    ontoggle: vi.fn(),
    oncreatechild: vi.fn(),
    onstartrename: vi.fn(),
    oncommitrename: vi.fn(),
    oncancelrename: vi.fn(),
    ondelete: vi.fn(),
    onstartdrag: vi.fn(),
    onenddrag: vi.fn(),
    ondrop: vi.fn(),
    ...overrides,
  };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = baseProps(overrides);
  const comp = mount(KBTree, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("KBTree — rendering", () => {
  it("renders root-level pages sorted by order", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "b", title: "B", order: 1 }), makeEntry({ id: "a", title: "A", order: 0 })],
    });
    const titles = Array.from(target.querySelectorAll(".page-title")).map((n) => n.textContent);
    expect(titles).toEqual(["A", "B"]);
    unmount(comp); target.remove();
  });

  it("shows the page's icon, defaulting to 📄", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ icon: "🔧" }), makeEntry({ id: "e2", icon: "", order: 1 })],
    });
    const icons = Array.from(target.querySelectorAll(".page-icon")).map((n) => n.textContent);
    expect(icons).toContain("🔧");
    expect(icons).toContain("📄");
    unmount(comp); target.remove();
  });

  it("shows a disclosure triangle only for pages with children", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
    });
    expect(target.querySelectorAll(".disclosure").length).toBe(1);
    expect(target.querySelectorAll(".disclosure-spacer").length).toBe(1);
    unmount(comp); target.remove();
  });

  it("renders a live page whose parent no longer exists as top-level", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "orphan", parentId: "trashed-parent" })],
    });
    expect(target.querySelectorAll(".tree-row").length).toBe(1);
    expect(target.querySelector(".page-title")?.textContent).toBe("How to paint");
    unmount(comp); target.remove();
  });

  it("does not render children of a collapsed page", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      collapsedIds: new Set(["p"]),
    });
    expect(target.querySelectorAll(".tree-row").length).toBe(1);
    unmount(comp); target.remove();
  });

  it("shows empty state when there are no pages", () => {
    const { target, comp } = setup();
    expect(target.textContent).toContain("No pages yet.");
    unmount(comp); target.remove();
  });
});

describe("KBTree — selection", () => {
  it("clicking a row calls onselect with the entry", () => {
    const onselect = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], onselect });
    (target.querySelector(".tree-row") as HTMLElement).click();
    expect(onselect).toHaveBeenCalledWith(expect.objectContaining({ id: "e1" }));
    unmount(comp); target.remove();
  });

  it("marks the selected row active", () => {
    const { target, comp } = setup({ entries: [makeEntry()], selectedId: "e1" });
    expect(target.querySelector(".tree-row")?.className).toContain("active");
    unmount(comp); target.remove();
  });

  it("clicking the disclosure triangle toggles without selecting", () => {
    const onselect = vi.fn();
    const ontoggle = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      onselect, ontoggle,
    });
    (target.querySelector(".disclosure") as HTMLElement).click();
    expect(ontoggle).toHaveBeenCalledWith("p");
    expect(onselect).not.toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});

describe("KBTree — search filtering", () => {
  it("keeps a page visible if its own title matches", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "a", title: "Alpha" }), makeEntry({ id: "b", title: "Beta", order: 1 })],
      searchQuery: "alp",
    });
    expect(target.querySelectorAll(".page-title").length).toBe(1);
    unmount(comp); target.remove();
  });

  it("keeps a parent visible (and auto-expanded) if a descendant matches", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p", title: "Parent" }), makeEntry({ id: "c", title: "Matching child", parentId: "p", order: 0 })],
      collapsedIds: new Set(["p"]),
      searchQuery: "matching",
    });
    const titles = Array.from(target.querySelectorAll(".page-title")).map((n) => n.textContent);
    expect(titles).toEqual(["Parent", "Matching child"]);
    unmount(comp); target.remove();
  });
});

describe("KBTree — creation and rename", () => {
  it("clicking add-child calls oncreatechild with the page id", () => {
    const oncreatechild = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], oncreatechild });
    (target.querySelector(".add-child") as HTMLElement).click();
    expect(oncreatechild).toHaveBeenCalledWith("e1");
    unmount(comp); target.remove();
  });

  it("shows a rename input when renamingId matches, and commits on Enter", () => {
    const oncommitrename = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], renamingId: "e1", oncommitrename });
    const input = target.querySelector(".rename-input") as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "Renamed title";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(oncommitrename).toHaveBeenCalledWith("e1", "Renamed title");
    unmount(comp); target.remove();
  });
});

describe("KBTree — drag and drop", () => {
  it("dropping in the middle band of a row calls ondrop with orderedIds null (nest)", () => {
    const ondrop = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "a" }), makeEntry({ id: "b", order: 1 })],
      dragging: "a", ondrop,
    });
    const rows = target.querySelectorAll(".tree-row");
    const targetRow = rows[1] as HTMLElement;
    vi.spyOn(targetRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    targetRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 10 }));
    targetRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 10 }));
    expect(ondrop).toHaveBeenCalledWith("a", "b", null);
    unmount(comp); target.remove();
  });

  it("dropping in the top band of a row calls ondrop with a before-reordered sibling list", () => {
    const ondrop = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "a" }), makeEntry({ id: "b", order: 1 }), makeEntry({ id: "c", order: 2 })],
      dragging: "c", ondrop,
    });
    const rows = target.querySelectorAll(".tree-row");
    const targetRow = rows[0] as HTMLElement;
    vi.spyOn(targetRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    targetRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 1 }));
    targetRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 1 }));
    expect(ondrop).toHaveBeenCalledWith("c", null, ["c", "a", "b"]);
    unmount(comp); target.remove();
  });

  it("does not call ondrop when dropping a page onto its own descendant", () => {
    const ondrop = vi.fn();
    const { target, comp } = setup({
      entries: [makeEntry({ id: "p" }), makeEntry({ id: "c", parentId: "p", order: 0 })],
      dragging: "p", ondrop,
    });
    const rows = target.querySelectorAll(".tree-row");
    const childRow = rows[1] as HTMLElement;
    vi.spyOn(childRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    childRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 10 }));
    childRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 10 }));
    expect(ondrop).not.toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});
