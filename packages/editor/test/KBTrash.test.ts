import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBTrash from "../src/lib/components/ui/KBTrash.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "Old note", content: "", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], parentId: null, icon: "📄", order: 0,
    deletedAt: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = {
    entries: [] as KBEntry[],
    onrestore: vi.fn(),
    ondeleteforever: vi.fn(),
    onemptytrash: vi.fn(),
    ...overrides,
  };
  const comp = mount(KBTrash, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("KBTrash", () => {
  it("shows empty state when trash is empty", () => {
    const { target, comp } = setup();
    expect(target.textContent).toContain("Trash is empty.");
    unmount(comp); target.remove();
  });

  it("lists each trashed page with its title and icon", () => {
    const { target, comp } = setup({ entries: [makeEntry({ icon: "🔧" })] });
    expect(target.querySelector(".trash-title")?.textContent).toBe("Old note");
    expect(target.querySelector(".trash-icon")?.textContent).toBe("🔧");
    unmount(comp); target.remove();
  });

  it("clicking Restore calls onrestore with the entry id", () => {
    const onrestore = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], onrestore });
    const restoreBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Restore") as HTMLElement;
    restoreBtn.click();
    expect(onrestore).toHaveBeenCalledWith("e1");
    unmount(comp); target.remove();
  });

  it("delete forever requires confirmation before calling ondeleteforever", () => {
    const ondeleteforever = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], ondeleteforever });
    (target.querySelector('[title="Delete forever"]') as HTMLElement).click();
    flushSync();
    expect(ondeleteforever).not.toHaveBeenCalled();
    const confirmBtn = target.querySelector(".trash-actions button.ui-button-danger") as HTMLElement;
    confirmBtn.click();
    expect(ondeleteforever).toHaveBeenCalledWith("e1");
    unmount(comp); target.remove();
  });

  it("does not show Empty Trash button when trash is empty", () => {
    const { target, comp } = setup();
    const emptyBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Empty Trash");
    expect(emptyBtn).toBeUndefined();
    unmount(comp); target.remove();
  });

  it("Empty Trash requires confirmation before calling onemptytrash", () => {
    const onemptytrash = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry()], onemptytrash });
    const emptyBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Empty Trash") as HTMLElement;
    emptyBtn.click();
    flushSync();
    expect(onemptytrash).not.toHaveBeenCalled();
    const confirmBtn = target.querySelector(".trash-header button.ui-button-danger") as HTMLElement;
    confirmBtn.click();
    expect(onemptytrash).toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});
