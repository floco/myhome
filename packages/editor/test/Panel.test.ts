import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Panel from "../src/lib/components/ui/Panel.svelte";

describe("ui/Panel", () => {
  it("defaults to normal density", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Panel, { target, props: {} });

    expect(target.querySelector(".ui-panel-normal")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("applies compact density when requested", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Panel, { target, props: { density: "compact" } });

    expect(target.querySelector(".ui-panel-compact")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
