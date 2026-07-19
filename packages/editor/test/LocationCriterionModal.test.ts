import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationCriterionModal from "../src/lib/components/LocationCriterionModal.svelte";

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("LocationCriterionModal", () => {
  it("create mode: Save is disabled until a name is entered, then calls onsave with entered values", () => {
    const onsave = vi.fn();
    const onclose = vi.fn();
    const el = target();
    const comp = mount(LocationCriterionModal, { target: el, props: { criterion: null, onsave, onclose } });
    flushSync();
    const saveBtn = Array.from(el.querySelectorAll("button")).find((b) => b.textContent === "Add") as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);

    const nameInput = el.querySelector(".ui-input") as HTMLInputElement;
    nameInput.value = "Safety";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(saveBtn.disabled).toBe(false);

    saveBtn.click();
    expect(onsave).toHaveBeenCalledWith({ name: "Safety", description: "", weight: "medium" });
    expect(onclose).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });

  it("edit mode: pre-fills from the passed criterion and calls onsave on Save", () => {
    const onsave = vi.fn();
    const el = target();
    const comp = mount(LocationCriterionModal, {
      target: el,
      props: {
        criterion: { id: "c1", name: "Cost of Living", description: "Land & construction", weight: "high" },
        onsave, onclose: vi.fn(),
      },
    });
    flushSync();
    const nameInput = el.querySelector(".ui-input") as HTMLInputElement;
    expect(nameInput.value).toBe("Cost of Living");
    const textarea = el.querySelector(".native-textarea") as HTMLTextAreaElement;
    expect(textarea.value).toBe("Land & construction");
    const select = el.querySelector(".native-select") as HTMLSelectElement;
    expect(select.value).toBe("high");

    const saveBtn = Array.from(el.querySelectorAll("button")).find((b) => b.textContent === "Save") as HTMLButtonElement;
    saveBtn.click();
    expect(onsave).toHaveBeenCalledWith({ name: "Cost of Living", description: "Land & construction", weight: "high" });
    unmount(comp);
    el.remove();
  });
});
