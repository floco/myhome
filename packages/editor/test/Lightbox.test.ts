import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import Lightbox from "../src/lib/components/ui/Lightbox.svelte";
import type { MediaItem } from "../src/lib/components/ui/mediaTypes";

function makeItem(overrides: Partial<MediaItem> = {}): MediaItem {
  return {
    id: "photo.jpg",
    name: "photo.jpg",
    url: "/api/works/w1/attachments/photo.jpg",
    thumbnailUrl: "/api/works/w1/attachments/photo.jpg",
    type: "image",
    ...overrides,
  };
}

function setup(props: Record<string, unknown>) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(Lightbox, { target, props });
  return { target, comp };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("Lightbox — rendering", () => {
  it("renders the overlay", () => {
    const { target, comp } = setup({ items: [makeItem()], initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-overlay")).not.toBeNull();
    unmount(comp);
  });

  it("shows the filename and counter", () => {
    const items = [makeItem({ name: "photo.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("photo.jpg");
    expect(target.querySelector(".lightbox-counter")!.textContent).toContain("1 / 2");
    unmount(comp);
  });

  it("renders an img for image items", () => {
    const { target, comp } = setup({ items: [makeItem({ type: "image" })], initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-img")).not.toBeNull();
    unmount(comp);
  });

  it("renders a thumbnail and Open button for document items", () => {
    const item = makeItem({ type: "document", name: "invoice.pdf", url: "/api/works/w1/attachments/invoice.pdf" });
    const { target, comp } = setup({ items: [item], initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-img")).not.toBeNull();
    const openBtn = target.querySelector(".lightbox-open-btn") as HTMLAnchorElement;
    expect(openBtn).not.toBeNull();
    expect(openBtn.href).toContain("invoice.pdf");
    unmount(comp);
  });
});

describe("Lightbox — navigation", () => {
  it("hides left arrow on first item", () => {
    const items = [makeItem(), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".arrow-prev")).toBeNull();
    unmount(comp);
  });

  it("hides right arrow on last item", () => {
    const items = [makeItem(), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 1, onclose: vi.fn() });
    expect(target.querySelector(".arrow-next")).toBeNull();
    unmount(comp);
  });

  it("clicking right arrow advances to next item", () => {
    const items = [makeItem({ name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    (target.querySelector(".arrow-next") as HTMLElement).click();
    flushSync();
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("b.jpg");
    unmount(comp);
  });

  it("clicking left arrow goes back to previous item", () => {
    const items = [makeItem({ name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 1, onclose: vi.fn() });
    (target.querySelector(".arrow-prev") as HTMLElement).click();
    flushSync();
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("a.jpg");
    unmount(comp);
  });
});

describe("Lightbox — close", () => {
  it("calls onclose when clicking the backdrop", () => {
    const onclose = vi.fn();
    const { target, comp } = setup({ items: [makeItem()], initialIndex: 0, onclose });
    (target.querySelector(".lightbox-overlay") as HTMLElement).click();
    expect(onclose).toHaveBeenCalledOnce();
    unmount(comp);
  });

  it("calls onclose on Escape key", async () => {
    const onclose = vi.fn();
    const { target, comp } = setup({ items: [makeItem()], initialIndex: 0, onclose });
    await tick(); // wait for onMount to register the keydown listener
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(onclose).toHaveBeenCalledOnce();
    unmount(comp);
  });

  it("navigates with arrow keys", async () => {
    const items = [makeItem({ name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    await tick(); // wait for onMount
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
    flushSync();
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("b.jpg");
    unmount(comp);
  });
});
