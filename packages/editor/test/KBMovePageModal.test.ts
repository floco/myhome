import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBMovePageModal from "../src/lib/components/ui/KBMovePageModal.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "How to paint", content: "", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], parentId: null, icon: "📄", order: 0,
    ...overrides,
  };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = {
    open: true,
    entries: [] as KBEntry[],
    pageId: "e1",
    onmove: vi.fn(),
    onclose: vi.fn(),
    ...overrides,
  };
  const comp = mount(KBMovePageModal, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("KBMovePageModal", () => {
  it("lists other pages as move targets, showing a breadcrumb path", () => {
    const entries = [
      makeEntry({ id: "a", title: "Kitchen" }),
      makeEntry({ id: "b", title: "Appliances", parentId: "a", order: 0 }),
      makeEntry({ id: "e1", title: "Fridge manual", order: 1 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1" });
    const texts = Array.from(target.querySelectorAll(".move-item")).map((b) => b.textContent);
    expect(texts.some((t) => t?.includes("Kitchen"))).toBe(true);
    expect(texts.some((t) => t?.includes("Kitchen › Appliances"))).toBe(true);
    unmount(comp); target.remove();
  });

  it("excludes the page itself and its descendants", () => {
    const entries = [
      makeEntry({ id: "e1", title: "Parent" }),
      makeEntry({ id: "child", title: "Child", parentId: "e1", order: 0 }),
      makeEntry({ id: "grandchild", title: "Grandchild", parentId: "child", order: 0 }),
      makeEntry({ id: "other", title: "Other", order: 1 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1" });
    const texts = Array.from(target.querySelectorAll(".move-item")).map((b) => b.textContent);
    expect(texts.some((t) => t?.includes("Parent"))).toBe(false);
    expect(texts.some((t) => t?.includes("Child"))).toBe(false);
    expect(texts.some((t) => t?.includes("Grandchild"))).toBe(false);
    expect(texts.some((t) => t?.includes("Other"))).toBe(true);
    unmount(comp); target.remove();
  });

  it("excludes the page's current parent from the candidate list", () => {
    const entries = [
      makeEntry({ id: "a", title: "Current parent" }),
      makeEntry({ id: "e1", title: "This page", parentId: "a", order: 0 }),
      makeEntry({ id: "b", title: "Another page", order: 1 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1" });
    const texts = Array.from(target.querySelectorAll(".move-item")).map((b) => b.textContent);
    expect(texts.some((t) => t?.includes("Current parent"))).toBe(false);
    expect(texts.some((t) => t?.includes("Another page"))).toBe(true);
    unmount(comp); target.remove();
  });

  it("shows a top-level option only when the page currently has a parent", () => {
    const entries = [
      makeEntry({ id: "a", title: "Parent" }),
      makeEntry({ id: "e1", title: "This page", parentId: "a", order: 0 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1" });
    expect(Array.from(target.querySelectorAll(".move-item")).some((b) => b.textContent?.includes("Top level (no parent)"))).toBe(true);
    unmount(comp); target.remove();
  });

  it("hides the top-level option when the page is already top-level", () => {
    const entries = [
      makeEntry({ id: "e1", title: "This page" }),
      makeEntry({ id: "b", title: "Other", order: 1 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1" });
    expect(Array.from(target.querySelectorAll(".move-item")).some((b) => b.textContent?.includes("Top level (no parent)"))).toBe(false);
    unmount(comp); target.remove();
  });

  it("filters candidates by search query", () => {
    const entries = [
      makeEntry({ id: "e1", title: "This page" }),
      makeEntry({ id: "a", title: "Kitchen", order: 1 }),
      makeEntry({ id: "b", title: "Garage", order: 2 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1" });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "kit";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const texts = Array.from(target.querySelectorAll(".move-item")).map((b) => b.textContent);
    expect(texts.some((t) => t?.includes("Kitchen"))).toBe(true);
    expect(texts.some((t) => t?.includes("Garage"))).toBe(false);
    unmount(comp); target.remove();
  });

  it("calls onmove with the target id when a candidate is clicked", () => {
    const onmove = vi.fn();
    const entries = [
      makeEntry({ id: "e1", title: "This page" }),
      makeEntry({ id: "a", title: "Other page", order: 1 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1", onmove });
    (target.querySelector(".move-item") as HTMLElement).click();
    expect(onmove).toHaveBeenCalledWith("a");
    unmount(comp); target.remove();
  });

  it("calls onmove with null when the top-level option is clicked", () => {
    const onmove = vi.fn();
    const entries = [
      makeEntry({ id: "a", title: "Parent" }),
      makeEntry({ id: "e1", title: "This page", parentId: "a", order: 0 }),
    ];
    const { target, comp } = setup({ entries, pageId: "e1", onmove });
    const topLevel = Array.from(target.querySelectorAll(".move-item"))
      .find((b) => b.textContent?.includes("Top level (no parent)")) as HTMLElement;
    topLevel.click();
    expect(onmove).toHaveBeenCalledWith(null);
    unmount(comp); target.remove();
  });

  it("shows an empty-state message when there are no other pages to move to", () => {
    const entries = [makeEntry({ id: "e1", title: "Only page" })];
    const { target, comp } = setup({ entries, pageId: "e1" });
    expect(target.textContent).toContain("No other pages to move to.");
    unmount(comp); target.remove();
  });
});
