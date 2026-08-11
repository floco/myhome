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
});
