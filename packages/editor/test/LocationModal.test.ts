import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationModal from "../src/lib/components/LocationModal.svelte";

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("LocationModal", () => {
  it("create mode: Save is disabled until a name is entered, then calls onsave with entered values", () => {
    const onsave = vi.fn();
    const onclose = vi.fn();
    const el = target();
    const comp = mount(LocationModal, { target: el, props: { location: null, onsave, onclose } });
    flushSync();
    const saveBtn = Array.from(el.querySelectorAll("button")).find((b) => b.textContent === "Add") as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);

    const nameInput = el.querySelector(".ui-input") as HTMLInputElement;
    nameInput.value = "Nantes";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(saveBtn.disabled).toBe(false);

    saveBtn.click();
    expect(onsave).toHaveBeenCalledWith({ name: "Nantes", emoji: "📍" });
    expect(onclose).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });

  it("edit mode: pre-fills from the passed location and calls onsave on Save", () => {
    const onsave = vi.fn();
    const el = target();
    const comp = mount(LocationModal, {
      target: el,
      props: { location: { id: "l1", name: "Ljubljana", emoji: "🇸🇮" }, onsave, onclose: vi.fn() },
    });
    flushSync();
    const nameInput = el.querySelector(".ui-input") as HTMLInputElement;
    expect(nameInput.value).toBe("Ljubljana");
    expect(el.querySelector(".ep-current")?.textContent).toBe("🇸🇮");

    const saveBtn = Array.from(el.querySelectorAll("button")).find((b) => b.textContent === "Save") as HTMLButtonElement;
    saveBtn.click();
    expect(onsave).toHaveBeenCalledWith({ name: "Ljubljana", emoji: "🇸🇮" });
    unmount(comp);
    el.remove();
  });
});
