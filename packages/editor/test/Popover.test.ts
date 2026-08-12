import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import Popover from "../src/lib/components/ui/Popover.svelte";

describe("ui/Popover", () => {
  it("renders nothing when closed", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const comp = mount(Popover, { target, props: { open: false, anchorEl: anchor, onclose: vi.fn() } });

    expect(document.querySelector(".ui-popover")).toBeNull();

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("renders the panel when open", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose: vi.fn() } });

    expect(document.querySelector(".ui-popover")).not.toBeNull();

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("calls onclose when clicking outside the panel and the anchor", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const onclose = vi.fn();
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose } });

    document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("calls onclose on Escape", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const onclose = vi.fn();
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose } });

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("applies a custom width when provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose: vi.fn(), width: 280 } });

    const panel = document.querySelector(".ui-popover") as HTMLElement;
    expect(panel.style.width).toBe("280px");

    unmount(comp);
    target.remove();
    anchor.remove();
  });

  it("has no explicit width style when width is omitted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const comp = mount(Popover, { target, props: { open: true, anchorEl: anchor, onclose: vi.fn() } });

    const panel = document.querySelector(".ui-popover") as HTMLElement;
    expect(panel.style.width).toBe("");

    unmount(comp);
    target.remove();
    anchor.remove();
  });
});
