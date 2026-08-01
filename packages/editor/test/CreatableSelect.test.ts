import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CreatableSelect from "../src/lib/components/ui/CreatableSelect.svelte";

afterEach(() => { document.body.innerHTML = ""; });

const OPTIONS = [
  { id: "o1", name: "Alice" },
  { id: "o2", name: "Bob" },
];

describe("CreatableSelect", () => {
  it("shows the selected option's name when closed", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: "o2", options: OPTIONS, oncreate: vi.fn() },
    });
    flushSync();
    expect((target.querySelector(".cs-input") as HTMLInputElement).value).toBe("Bob");
    unmount(comp);
  });

  it("opens the panel on focus and filters options as you type", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate: vi.fn() },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    input.value = "ali";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const labels = Array.from(document.querySelectorAll(".cs-option")).map((el) => el.textContent?.trim());
    expect(labels).toContain("Alice");
    expect(labels).not.toContain("Bob");
    unmount(comp);
  });

  it("selecting an existing option calls onchange with its id and closes the panel", () => {
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate: vi.fn(), onchange },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    (document.querySelector(".cs-option") as HTMLElement).click();
    flushSync();
    expect(onchange).toHaveBeenCalledWith("o1");
    expect(document.querySelector(".cs-panel")).toBeNull();
    unmount(comp);
  });

  it("typing a brand-new name shows a create row that calls oncreate and adopts the returned id", async () => {
    const oncreate = vi.fn().mockResolvedValue({ id: "o3", name: "Carol" });
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate, onchange },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    input.value = "Carol";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const createRow = document.querySelector(".cs-create") as HTMLElement;
    expect(createRow.textContent).toContain("Carol");
    createRow.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(oncreate).toHaveBeenCalledWith("Carol");
    expect(onchange).toHaveBeenCalledWith("o3");
    unmount(comp);
  });

  it("does not show a create row when the typed text exactly matches an existing option", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate: vi.fn() },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    input.value = "alice";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(document.querySelector(".cs-create")).toBeNull();
    unmount(comp);
  });

  it("clicking the clear button calls onchange with null", () => {
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: "o1", options: OPTIONS, oncreate: vi.fn(), onchange },
    });
    flushSync();
    (target.querySelector(".cs-clear") as HTMLElement).click();
    flushSync();
    expect(onchange).toHaveBeenCalledWith(null);
    unmount(comp);
  });
});
