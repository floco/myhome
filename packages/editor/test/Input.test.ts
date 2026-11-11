import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
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

  it("renders a label tied to the input when one is given", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: { label: "Current password", type: "password" } });

    const label = target.querySelector("label")!;
    expect(label.textContent).toContain("Current password");
    expect(label.querySelector("input.ui-input")?.getAttribute("type")).toBe("password");

    unmount(comp);
    target.remove();
  });

  it("renders no label element without a label", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Input, { target, props: {} });
    expect(target.querySelector("label")).toBeNull();
    unmount(comp);
    target.remove();
  });

  it("passes other attributes and event handlers through to the input", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onkeydown = vi.fn();
    const comp = mount(Input, { target, props: { type: "number", min: "0", step: "any", onkeydown } });
    flushSync();

    const input = target.querySelector("input")!;
    expect(input.getAttribute("min")).toBe("0");
    expect(input.getAttribute("step")).toBe("any");
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(onkeydown).toHaveBeenCalledTimes(1);

    unmount(comp);
    target.remove();
  });
});
