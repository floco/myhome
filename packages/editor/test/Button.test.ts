import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import Button from "../src/lib/components/ui/Button.svelte";

describe("ui/Button", () => {
  it("defaults to the primary variant", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Button, { target, props: {} });

    const btn = target.querySelector("button")!;
    expect(btn.classList.contains("ui-button-primary")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("applies the requested variant class", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Button, { target, props: { variant: "secondary" } });

    const btn = target.querySelector("button")!;
    expect(btn.classList.contains("ui-button-secondary")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("calls onclick when clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclick = vi.fn();
    const comp = mount(Button, { target, props: { onclick } });

    target.querySelector("button")!.click();
    expect(onclick).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("does not call onclick when disabled", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclick = vi.fn();
    const comp = mount(Button, { target, props: { onclick, disabled: true } });

    const btn = target.querySelector("button")!;
    expect(btn.disabled).toBe(true);
    btn.click();
    expect(onclick).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });

  it("supports the danger variant", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Button, { target, props: { variant: "danger" } });

    const btn = target.querySelector("button")!;
    expect(btn.classList.contains("ui-button-danger")).toBe(true);

    unmount(comp);
    target.remove();
  });
});
