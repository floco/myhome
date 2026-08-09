import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import FurnitureParamsPanel from "../src/lib/components/FurnitureParamsPanel.svelte";
import { getTemplate } from "../src/lib/furnitureLibrary";
import type { FurnitureObject } from "@myhome/geometry";

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const object: FurnitureObject = { id: "f1", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 0.9, rotation: 0 };
  const props = {
    object,
    template: getTemplate("sofa")!,
    onupdate: vi.fn(),
    ...overrides,
  };
  const comp = mount(FurnitureParamsPanel, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("FurnitureParamsPanel", () => {
  it("renders a select for each enum param, showing the resolved default value", () => {
    const { target, comp } = setup();
    const selects = target.querySelectorAll("select");
    expect(selects).toHaveLength(1); // shape is visible; corner is hidden (visibleWhen shape=l-shaped, default is straight)
    expect((selects[0] as HTMLSelectElement).value).toBe("straight");
    unmount(comp); target.remove();
  });

  it("shows the corner select once shape is l-shaped", () => {
    const object: FurnitureObject = { id: "f1", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 0.9, rotation: 0, params: { shape: "l-shaped" } };
    const { target, comp } = setup({ object });
    const selects = target.querySelectorAll("select");
    expect(selects).toHaveLength(2);
    unmount(comp); target.remove();
  });

  it("calls onupdate with the param id and new value when a select changes", () => {
    const onupdate = vi.fn();
    const { target, comp } = setup({ onupdate });
    const select = target.querySelector("select") as HTMLSelectElement;
    select.value = "l-shaped";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ shape: "l-shaped" });
    unmount(comp); target.remove();
  });

  it("renders a number input for integer params, e.g. chairCount on a table", () => {
    const object: FurnitureObject = { id: "f2", templateId: "dining-table-rect", x: 0, y: 0, width: 1.6, height: 0.9, rotation: 0 };
    const { target, comp } = setup({ object, template: getTemplate("dining-table-rect")! });
    const input = target.querySelector('input[type="number"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.value).toBe("4");
    unmount(comp); target.remove();
  });

  it("calls onupdate with a numeric value when a number input changes", () => {
    const onupdate = vi.fn();
    const object: FurnitureObject = { id: "f2", templateId: "dining-table-rect", x: 0, y: 0, width: 1.6, height: 0.9, rotation: 0 };
    const { target, comp } = setup({ object, template: getTemplate("dining-table-rect")!, onupdate });
    const input = target.querySelector('input[type="number"]') as HTMLInputElement;
    input.value = "6";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ chairCount: 6 });
    unmount(comp); target.remove();
  });

  it("calls ondismiss when the close button is clicked", () => {
    const ondismiss = vi.fn();
    const { target, comp } = setup({ ondismiss });
    (target.querySelector('[title="Close"]') as HTMLElement).click();
    expect(ondismiss).toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});
