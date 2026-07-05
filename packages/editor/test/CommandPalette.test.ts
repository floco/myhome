import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CommandPalette from "../src/lib/components/CommandPalette.svelte";
import type { SearchResult } from "../src/lib/searchIndex";

afterEach(() => { document.body.innerHTML = ""; });

const INDEX: SearchResult[] = [
  { module: "chores", id: "c1", icon: "🧹", title: "Sweep kitchen", subtitle: "Aug 1, 2026", searchText: "sweep kitchen home", titleText: "sweep kitchen" },
  { module: "inventory", id: "i1", icon: "📺", title: "Samsung TV", subtitle: "Electronics", searchText: "samsung tv home", titleText: "samsung tv" },
];

function mountPalette(props: { open: boolean; index: SearchResult[]; onclose: () => void; onselect: (r: SearchResult) => void }) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(CommandPalette, { target, props });
  flushSync();
  return { target, comp };
}

describe("CommandPalette", () => {
  it("renders nothing when closed", () => {
    const { target, comp } = mountPalette({ open: false, index: INDEX, onclose: vi.fn(), onselect: vi.fn() });
    expect(target.querySelector(".cmdk")).toBeNull();
    unmount(comp);
  });

  it("shows no results below the minimum query length", async () => {
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect: vi.fn() });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "s";
    input.dispatchEvent(new Event("input"));
    flushSync();
    expect(target.querySelectorAll(".cmdk-result").length).toBe(0);
    unmount(comp);
  });

  it("filters results as the query changes and groups them by module", async () => {
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect: vi.fn() });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "samsung";
    input.dispatchEvent(new Event("input"));
    flushSync();
    const results = target.querySelectorAll(".cmdk-result");
    expect(results.length).toBe(1);
    expect(results[0].textContent).toContain("Samsung TV");
    expect(target.querySelector(".cmdk-group-label")?.textContent).toBe("Inventory");
    unmount(comp);
  });

  it("calls onselect with the highlighted result on Enter", async () => {
    const onselect = vi.fn();
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "sweep";
    input.dispatchEvent(new Event("input"));
    flushSync();
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();
    expect(onselect).toHaveBeenCalledWith(INDEX[0]);
    unmount(comp);
  });

  it("moves the highlight with ArrowDown and selects the second result", async () => {
    // Both fixture entries share the word "home" in their searchText,
    // so this query surfaces both, in fixed module order (chores before inventory).
    const onselect = vi.fn();
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose: vi.fn(), onselect });
    const input = target.querySelector("input") as HTMLInputElement;
    input.value = "home";
    input.dispatchEvent(new Event("input"));
    flushSync();
    expect(target.querySelectorAll(".cmdk-result").length).toBe(2);

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    flushSync();
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();

    expect(onselect).toHaveBeenCalledWith(INDEX[1]);
    unmount(comp);
  });

  it("closes on Escape without selecting anything", () => {
    const onclose = vi.fn();
    const onselect = vi.fn();
    const { target, comp } = mountPalette({ open: true, index: INDEX, onclose, onselect });
    const input = target.querySelector("input") as HTMLInputElement;
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    flushSync();
    expect(onclose).toHaveBeenCalledOnce();
    expect(onselect).not.toHaveBeenCalled();
    unmount(comp);
  });
});
