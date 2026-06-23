import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import StatTile from "../src/lib/components/ui/StatTile.svelte";

describe("ui/StatTile", () => {
  it("renders the value and label", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 128, label: "Items" } });

    expect(target.querySelector(".ui-stat-value")!.textContent).toBe("128");
    expect(target.querySelector(".ui-stat-label")!.textContent).toBe("Items");

    unmount(comp);
    target.remove();
  });

  it("accepts a string value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: "18.6k km", label: "Distance" } });

    expect(target.querySelector(".ui-stat-value")!.textContent).toBe("18.6k km");

    unmount(comp);
    target.remove();
  });
});
