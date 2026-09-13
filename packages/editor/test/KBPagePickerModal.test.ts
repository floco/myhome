import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBPagePickerModal from "../src/lib/components/ui/KBPagePickerModal.svelte";
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
    onselect: vi.fn(),
    onclose: vi.fn(),
    ...overrides,
  };
  const comp = mount(KBPagePickerModal, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("KBPagePickerModal", () => {
  it("lists every page with a breadcrumb path", () => {
    const entries = [
      makeEntry({ id: "a", title: "Kitchen" }),
      makeEntry({ id: "b", title: "Appliances", parentId: "a", order: 0 }),
    ];
    const { target, comp } = setup({ entries });
    const texts = Array.from(target.querySelectorAll(".picker-item")).map((b) => b.textContent);
    expect(texts.some((t) => t?.includes("Kitchen"))).toBe(true);
    expect(texts.some((t) => t?.includes("Kitchen › Appliances"))).toBe(true);
    unmount(comp); target.remove();
  });

  it("does not exclude the current page (unlike the move modal)", () => {
    const entries = [makeEntry({ id: "e1", title: "Self page" })];
    const { target, comp } = setup({ entries });
    expect(target.querySelector(".picker-item")?.textContent).toContain("Self page");
    unmount(comp); target.remove();
  });

  it("filters candidates by search query", () => {
    const entries = [
      makeEntry({ id: "a", title: "Kitchen" }),
      makeEntry({ id: "b", title: "Garage", order: 1 }),
    ];
    const { target, comp } = setup({ entries });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "kit";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const texts = Array.from(target.querySelectorAll(".picker-item")).map((b) => b.textContent);
    expect(texts.some((t) => t?.includes("Kitchen"))).toBe(true);
    expect(texts.some((t) => t?.includes("Garage"))).toBe(false);
    unmount(comp); target.remove();
  });

  it("calls onselect with the chosen entry", () => {
    const onselect = vi.fn();
    const entries = [makeEntry({ id: "a", title: "Kitchen" })];
    const { target, comp } = setup({ entries, onselect });
    (target.querySelector(".picker-item") as HTMLElement).click();
    expect(onselect).toHaveBeenCalledWith(entries[0]);
    unmount(comp); target.remove();
  });

  it("shows an empty-state message when there are no pages", () => {
    const { target, comp } = setup({ entries: [] });
    expect(target.textContent).toContain("No pages yet.");
    unmount(comp); target.remove();
  });
});
