import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Input from "../src/lib/components/ui/Input.svelte";

describe("ui/Input", () => {
  it("renders the given value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: { value: "Garden Hose" } });

    const input = target.querySelector("input")!;
    expect(input.value).toBe("Garden Hose");

    unmount(comp);
    target.remove();
  });

  it("renders the placeholder when no value is set", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: { placeholder: "Search…" } });

    const input = target.querySelector("input")!;
    expect(input.placeholder).toBe("Search…");
    expect(input.value).toBe("");

    unmount(comp);
    target.remove();
  });

  it("applies the ui-input class", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: {} });

    expect(target.querySelector("input.ui-input")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
