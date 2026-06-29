import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, tick } from "svelte";
import WorkModal from "../src/lib/components/WorkModal.svelte";

function makeStore(attachments: string[] = []) {
  return {
    works: [{ id: "w1", title: "Boiler repair", description: "", status: "done", categoryId: null, date: "2025-11-10", totalCost: 1200, supplierId: null, notes: "", attachments, placement: null }],
    loaded: true,
    loadError: null,
    createWork: vi.fn(),
    updateWork: vi.fn(),
    deleteWork: vi.fn(),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn(),
    setPlacement: vi.fn(),
  };
}

function makeSettingsStore() {
  return { workCategories: [], suppliers: [] };
}

function setup(attachments: string[] = []) {
  const store = makeStore(attachments);
  const target = document.createElement("div");
  document.body.appendChild(target);
  const work = store.works[0];
  const comp = mount(WorkModal, {
    target,
    props: {
      work,
      store,
      settingsStore: makeSettingsStore(),
      onclose: vi.fn(),
    },
  });
  return { target, comp, store };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("WorkModal — Media tab", () => {
  it("has a Media tab (not Attachments)", () => {
    const { target, comp } = setup();
    const tabs = Array.from(target.querySelectorAll(".tab")).map((t) => t.textContent);
    expect(tabs.some((t) => t?.includes("Media"))).toBe(true);
    expect(tabs.some((t) => t?.includes("Attachments"))).toBe(false);
    unmount(comp);
  });

  it("shows MediaGallery when Media tab is active", async () => {
    const { target, comp } = setup(["photo.jpg"]);
    const mediaTab = Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media")) as HTMLElement;
    mediaTab.click();
    await tick();
    expect(target.querySelector(".drop-zone")).not.toBeNull();
    unmount(comp);
  });

  it("badge count includes both images and PDFs", () => {
    const { target, comp } = setup(["photo.jpg", "invoice.pdf"]);
    const mediaTab = Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media"));
    expect(mediaTab?.textContent).toContain("2");
    unmount(comp);
  });

  it("calls store.uploadAttachment for each uploaded file", async () => {
    const { target, comp, store } = setup();
    const mediaTab = Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media")) as HTMLElement;
    mediaTab.click();
    await tick();
    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    const zone = target.querySelector(".drop-zone") as HTMLElement;
    zone.dispatchEvent(Object.assign(new Event("drop"), { dataTransfer: { files: [file] } }));
    await tick();
    expect(store.uploadAttachment).toHaveBeenCalledWith("w1", file);
    unmount(comp);
  });
});
