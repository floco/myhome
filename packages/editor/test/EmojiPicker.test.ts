import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import EmojiPicker from "../src/lib/components/ui/EmojiPicker.svelte";

afterEach(() => vi.unstubAllGlobals());

describe("EmojiPicker", () => {
  it("displays the current value on the trigger", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange: vi.fn() } });
    flushSync();
    expect(target.querySelector(".ep-current")?.textContent).toBe("🔋");
    unmount(comp);
    target.remove();
  });

  it("panel is hidden initially", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange: vi.fn() } });
    flushSync();
    expect(document.querySelector(".ep-panel")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("opens the panel on trigger click", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange: vi.fn() } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    expect(document.querySelector(".ep-panel")).not.toBeNull();
    expect(document.querySelectorAll(".ep-emoji").length).toBeGreaterThan(10);
    unmount(comp);
    target.remove();
  });

  it("calls onchange and closes panel when grid emoji clicked", () => {
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    const first = document.querySelector(".ep-emoji") as HTMLElement;
    const firstText = first.textContent ?? "";
    first.click();
    flushSync();
    expect(onchange).toHaveBeenCalledWith(firstText);
    expect(document.querySelector(".ep-panel")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("applies custom emoji via ✓ button", () => {
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    const input = document.querySelector(".ep-custom-input") as HTMLInputElement;
    input.value = "🌟";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    (document.querySelector(".ep-apply") as HTMLElement).click();
    flushSync();
    expect(onchange).toHaveBeenCalledWith("🌟");
    expect(document.querySelector(".ep-panel")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("closes on Escape key", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange: vi.fn() } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    expect(document.querySelector(".ep-panel")).not.toBeNull();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    flushSync();
    expect(document.querySelector(".ep-panel")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("second click on trigger closes the panel", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange: vi.fn() } });
    flushSync();
    const trigger = target.querySelector(".ep-trigger") as HTMLElement;
    trigger.click();
    flushSync();
    expect(document.querySelector(".ep-panel")).not.toBeNull();
    trigger.click();
    flushSync();
    expect(document.querySelector(".ep-panel")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("does not render tabs when flags is false (default)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "🔋", onchange: vi.fn() } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    expect(document.querySelector(".tab-bar")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("renders Objects/Flags tabs when flags is true, defaulting to Objects", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "📍", onchange: vi.fn(), flags: true } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    const tabs = Array.from(document.querySelectorAll(".tab-bar .tab"));
    expect(tabs.map((t) => t.textContent)).toEqual(["Objects", "Flags"]);
    expect(document.querySelector(".tab.active")?.textContent).toBe("Objects");
    expect(document.querySelectorAll(".ep-flag-grid").length).toBe(0);
    unmount(comp);
    target.remove();
  });

  it("switching to the Flags tab renders flag buttons and the filter narrows them", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "📍", onchange: vi.fn(), flags: true } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    const tabs = Array.from(document.querySelectorAll(".tab-bar .tab")) as HTMLButtonElement[];
    tabs[1].click();
    flushSync();
    const flagGrid = document.querySelector(".ep-flag-grid");
    expect(flagGrid).not.toBeNull();
    const allFlagButtons = flagGrid!.querySelectorAll(".ep-emoji").length;
    expect(allFlagButtons).toBeGreaterThan(50);

    const filterInput = document.querySelector(".ep-flag-filter") as HTMLInputElement;
    filterInput.value = "france";
    filterInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const filteredButtons = flagGrid!.querySelectorAll(".ep-emoji");
    expect(filteredButtons.length).toBe(1);
    expect(filteredButtons[0].getAttribute("title")).toBe("France");
    unmount(comp);
    target.remove();
  });

  it("selecting a flag calls onchange with the flag string", () => {
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(EmojiPicker, { target, props: { value: "📍", onchange, flags: true } });
    flushSync();
    (target.querySelector(".ep-trigger") as HTMLElement).click();
    flushSync();
    const tabs = Array.from(document.querySelectorAll(".tab-bar .tab")) as HTMLButtonElement[];
    tabs[1].click();
    flushSync();
    const filterInput = document.querySelector(".ep-flag-filter") as HTMLInputElement;
    filterInput.value = "france";
    filterInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const flagBtn = document.querySelector(".ep-flag-grid .ep-emoji") as HTMLButtonElement;
    flagBtn.click();
    flushSync();
    expect(onchange).toHaveBeenCalledWith("🇫🇷");
    expect(document.querySelector(".ep-panel")).toBeNull();
    unmount(comp);
    target.remove();
  });
});
