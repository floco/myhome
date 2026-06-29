import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import MediaGallery from "../src/lib/components/ui/MediaGallery.svelte";
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
  const comp = mount(MediaGallery, { target, props });
  return { target, comp };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("MediaGallery — empty state", () => {
  it("shows empty state when no items", () => {
    const { target, comp } = setup({
      items: [],
      onUpload: vi.fn(),
      onDelete: vi.fn(),
      onItemClick: vi.fn(),
    });
    expect(target.textContent).toContain("No media yet");
    unmount(comp);
  });
});

describe("MediaGallery — grid view", () => {
  it("renders a tile per item in grid view", () => {
    const items = [makeItem({ id: "a.jpg", name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    expect(target.querySelectorAll(".media-tile").length).toBe(2);
    unmount(comp);
  });

  it("shows a PDF badge on document tiles", () => {
    const items = [makeItem({ id: "inv.pdf", name: "inv.pdf", type: "document" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    expect(target.querySelector(".pdf-badge")).not.toBeNull();
    unmount(comp);
  });

  it("calls onItemClick with the item index when tile is clicked", () => {
    const onItemClick = vi.fn();
    const items = [makeItem({ id: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick });
    (target.querySelectorAll(".media-tile")[1] as HTMLElement).click();
    expect(onItemClick).toHaveBeenCalledWith(1);
    unmount(comp);
  });

  it("calls onDelete with item id when delete button is clicked", () => {
    const onDelete = vi.fn();
    const items = [makeItem({ id: "photo.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete, onItemClick: vi.fn() });
    (target.querySelector(".tile-delete") as HTMLElement).click();
    expect(onDelete).toHaveBeenCalledWith("photo.jpg");
    unmount(comp);
  });
});

describe("MediaGallery — list view", () => {
  it("switches to list view when toggle is clicked", () => {
    const items = [makeItem()];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    (target.querySelector(".toggle-list") as HTMLElement).click();
    flushSync();
    expect(target.querySelector(".media-list-row")).not.toBeNull();
    expect(target.querySelector(".media-tile")).toBeNull();
    unmount(comp);
  });

  it("calls onItemClick when list row name is clicked", () => {
    const onItemClick = vi.fn();
    const items = [makeItem({ id: "photo.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick });
    (target.querySelector(".toggle-list") as HTMLElement).click();
    flushSync();
    (target.querySelector(".list-name") as HTMLElement).click();
    expect(onItemClick).toHaveBeenCalledWith(0);
    unmount(comp);
  });
});

describe("MediaGallery — upload", () => {
  it("renders a file input with multiple and accept attributes", () => {
    const { target, comp } = setup({ items: [], onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    const input = target.querySelector("input[type=file]") as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.multiple).toBe(true);
    expect(input.accept).toBe("image/*,.pdf");
    unmount(comp);
  });

  it("uses the accept prop on the file input", () => {
    const { target, comp } = setup({ items: [], accept: "image/*", onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    const input = target.querySelector("input[type=file]") as HTMLInputElement;
    expect(input.accept).toBe("image/*");
    unmount(comp);
  });

  it("shows uploading state when uploading prop is true", () => {
    const { target, comp } = setup({
      items: [],
      uploading: true,
      onUpload: vi.fn(),
      onDelete: vi.fn(),
      onItemClick: vi.fn(),
    });
    expect(target.textContent).toContain("Uploading");
    unmount(comp);
  });

  it("shows upload error when uploadError prop is set", () => {
    const { target, comp } = setup({
      items: [],
      uploadError: "Upload failed",
      onUpload: vi.fn(),
      onDelete: vi.fn(),
      onItemClick: vi.fn(),
    });
    expect(target.textContent).toContain("Upload failed");
    unmount(comp);
  });

  it("calls onUpload when files are dropped", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const { target, comp } = setup({ items: [], onUpload, onDelete: vi.fn(), onItemClick: vi.fn() });
    const zone = target.querySelector(".drop-zone") as HTMLElement;
    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    const dt = { files: [file] };
    zone.dispatchEvent(Object.assign(new Event("drop"), { dataTransfer: dt }));
    expect(onUpload).toHaveBeenCalledWith([file]);
    unmount(comp);
  });
});
