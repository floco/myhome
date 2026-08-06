import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LayersDropdown from "../src/lib/components/LayersDropdown.svelte";

function setup(activeLayers: Set<string>, ontoggle = vi.fn()) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(LayersDropdown, { target, props: { activeLayers, ontoggle } });
  flushSync();
  return { target, comp, ontoggle };
}

describe("LayersDropdown — ha layer", () => {
  it("renders a checked 'ha' row when the layer is active", () => {
    const { target, comp } = setup(new Set(["ha"]));
    (target.querySelector(".layers-btn") as HTMLButtonElement).click();
    flushSync();
    const haRow = Array.from(target.querySelectorAll(".layer-row")).find(
      (r) => r.textContent?.includes("Home Assistant"),
    ) as HTMLElement;
    expect(haRow).not.toBeUndefined();
    expect((haRow.querySelector('input[type="checkbox"]') as HTMLInputElement).checked).toBe(true);
    unmount(comp); target.remove();
  });

  it("calls ontoggle('ha') when the row is clicked", () => {
    const { target, comp, ontoggle } = setup(new Set(["ha"]));
    (target.querySelector(".layers-btn") as HTMLButtonElement).click();
    flushSync();
    const haRow = Array.from(target.querySelectorAll(".layer-row")).find(
      (r) => r.textContent?.includes("Home Assistant"),
    ) as HTMLElement;
    (haRow.querySelector('input[type="checkbox"]') as HTMLInputElement).dispatchEvent(
      new Event("change", { bubbles: true }),
    );
    expect(ontoggle).toHaveBeenCalledWith("ha");
    unmount(comp); target.remove();
  });
});
