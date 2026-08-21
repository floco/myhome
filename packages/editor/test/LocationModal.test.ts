import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import LocationModal from "../src/lib/components/LocationModal.svelte";

function makeStore(attachments: string[] = []) {
  return {
    locations: [{ id: "l1", name: "Ljubljana", emoji: "🇸🇮", notes: "", attachments }],
    createLocation: vi.fn(),
    updateLocation: vi.fn(),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn(),
  };
}

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("LocationModal", () => {
  it("create mode: Save is disabled until a name is entered, then calls store.createLocation", () => {
    const store = makeStore();
    const onclose = vi.fn();
    const el = target();
    const comp = mount(LocationModal, { target: el, props: { location: null, store, onclose } });
    flushSync();
    const saveBtn = Array.from(el.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Add") as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);

    const nameInput = el.querySelector(".ui-input") as HTMLInputElement;
    nameInput.value = "Nantes";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(saveBtn.disabled).toBe(false);

    saveBtn.click();
    expect(store.createLocation).toHaveBeenCalledWith({ name: "Nantes", emoji: "📍", notes: "" });
    unmount(comp);
  });

  it("edit mode: pre-fills from the passed location and calls store.updateLocation on Save", () => {
    const store = makeStore();
    const el = target();
    const comp = mount(LocationModal, {
      target: el,
      props: { location: store.locations[0], store, onclose: vi.fn() },
    });
    flushSync();
    const nameInput = el.querySelector(".ui-input") as HTMLInputElement;
    expect(nameInput.value).toBe("Ljubljana");
    expect(el.querySelector(".ep-current")?.textContent).toBe("🇸🇮");

    const saveBtn = Array.from(el.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Save") as HTMLButtonElement;
    saveBtn.click();
    expect(store.updateLocation).toHaveBeenCalledWith("l1", { name: "Ljubljana", emoji: "🇸🇮", notes: "" });
    unmount(comp);
  });

  it("has a Media tab disabled in create mode", () => {
    const store = makeStore();
    const el = target();
    const comp = mount(LocationModal, { target: el, props: { location: null, store, onclose: vi.fn() } });
    flushSync();
    const mediaTab = Array.from(el.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media")) as HTMLButtonElement;
    expect(mediaTab.disabled).toBe(true);
    unmount(comp);
  });

  it("badge count reflects attachments and media tab shows the gallery", async () => {
    const store = makeStore(["photo.jpg"]);
    const el = target();
    const comp = mount(LocationModal, { target: el, props: { location: store.locations[0], store, onclose: vi.fn() } });
    flushSync();
    const mediaTab = Array.from(el.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media")) as HTMLElement;
    expect(mediaTab.textContent).toContain("1");
    mediaTab.click();
    await tick();
    expect(el.querySelector(".drop-zone")).not.toBeNull();
    unmount(comp);
  });

  it("calls store.uploadAttachment for each uploaded file", async () => {
    const store = makeStore();
    const el = target();
    const comp = mount(LocationModal, { target: el, props: { location: store.locations[0], store, onclose: vi.fn() } });
    flushSync();
    const mediaTab = Array.from(el.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media")) as HTMLElement;
    mediaTab.click();
    await tick();
    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    const zone = el.querySelector(".drop-zone") as HTMLElement;
    zone.dispatchEvent(Object.assign(new Event("drop"), { dataTransfer: { files: [file] } }));
    await tick();
    expect(store.uploadAttachment).toHaveBeenCalledWith("l1", file);
    unmount(comp);
  });
});
