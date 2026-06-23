import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import Modal from "../src/lib/components/ui/Modal.svelte";

describe("ui/Modal", () => {
  it("renders nothing when closed", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Modal, { target, props: { open: false, title: "Edit item", onclose: vi.fn() } });

    expect(target.querySelector(".ui-modal")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("renders the dialog and title when open", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Modal, { target, props: { open: true, title: "Edit item", onclose: vi.fn() } });

    const dialog = target.querySelector(".ui-modal")!;
    expect(dialog).not.toBeNull();
    expect(dialog.querySelector(".ui-modal-title")!.textContent).toBe("Edit item");

    unmount(comp);
    target.remove();
  });

  it("calls onclose when the backdrop is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclose = vi.fn();
    const comp = mount(Modal, { target, props: { open: true, title: "Edit item", onclose } });

    (target.querySelector(".ui-modal-backdrop") as HTMLElement).click();
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("calls onclose when the close button is clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclose = vi.fn();
    const comp = mount(Modal, { target, props: { open: true, title: "Edit item", onclose } });

    (target.querySelector(".ui-modal-close") as HTMLElement).click();
    expect(onclose).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("defaults to 480px width", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Modal, { target, props: { open: true, title: "Edit item", onclose: vi.fn() } });

    const dialog = target.querySelector(".ui-modal") as HTMLElement;
    expect(dialog.style.width).toBe("480px");

    unmount(comp);
    target.remove();
  });

  it("applies a custom width when provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Modal, {
      target,
      props: { open: true, title: "Edit item", onclose: vi.fn(), width: "560px" },
    });

    const dialog = target.querySelector(".ui-modal") as HTMLElement;
    expect(dialog.style.width).toBe("560px");

    unmount(comp);
    target.remove();
  });
});
