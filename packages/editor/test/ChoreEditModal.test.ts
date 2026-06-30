import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import ChoreEditModal from "../src/lib/components/ChoreEditModal.svelte";
import type { Chore } from "../src/lib/choreStore.svelte";

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1",
    donetickId: null,
    name: "Sweep",
    emoji: "🧹",
    periodDays: 14,
    frequencyType: "interval",
    frequency: 14,
    frequencyMetadata: { unit: "days" },
    scheduleFromDue: false,
    nextDueDate: "2027-01-01T00:00:00Z",
    description: "",
    attachments: [],
    ...overrides,
  };
}

function makeStore(overrides = {}) {
  return {
    updateChore: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("ChoreEditModal — tabs", () => {
  it("shows Info and Media tab buttons when chore is provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, onclose: vi.fn() },
    });
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".modal-tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Info");
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    unmount(app);
    target.remove();
  });

  it("clicking Media tab renders drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore({ attachments: ["photo.jpg"] }), store: makeStore(), onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".modal-tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("Save calls updateChore with form values", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const onclose = vi.fn();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, onclose },
    });
    flushSync();
    const saveBtn = Array.from(target.querySelectorAll("button")).find(
      b => b.textContent?.trim() === "Save",
    ) as HTMLButtonElement;
    saveBtn.click();
    await tick();
    expect(store.updateChore).toHaveBeenCalledWith("c1", expect.objectContaining({ name: "Sweep" }));
    unmount(app);
    target.remove();
  });
});
