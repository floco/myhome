import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import KBPage from "../src/lib/components/KBPage.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1",
    title: "How to paint",
    content: "# Painting\n\nUse good brushes.",
    createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z",
    attachments: [],
    ...overrides,
  };
}

function makeStore(entries: KBEntry[] = [], overrides: Partial<ReturnType<typeof makeStore>> = {}) {
  return {
    entries,
    loaded: true,
    loadError: null as string | null,
    createEntry: vi.fn().mockResolvedValue(
      makeEntry({ id: "new1", title: "New entry", content: "" }),
    ),
    updateEntry: vi.fn().mockResolvedValue(undefined),
    deleteEntry: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("KBPage — entry list", () => {
  it("shows empty state when nothing is selected", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(KBPage, { target, props: { store: makeStore([makeEntry()]) } });
    flushSync();
    expect(target.querySelector(".content-empty")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("renders all entries in the sidebar", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([
      makeEntry({ id: "e1", title: "How to paint" }),
      makeEntry({ id: "e2", title: "Replace boiler" }),
    ]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const rows = target.querySelectorAll(".entry-row");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain("How to paint");
    expect(rows[1].textContent).toContain("Replace boiler");
    unmount(app);
    target.remove();
  });

  it("filters entries by search query", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([
      makeEntry({ id: "e1", title: "How to paint" }),
      makeEntry({ id: "e2", title: "Replace boiler" }),
    ]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const searchInput = target.querySelector(".kb-sidebar input") as HTMLInputElement;
    searchInput.value = "paint";
    searchInput.dispatchEvent(new Event("input"));
    flushSync();
    const rows = target.querySelectorAll(".entry-row");
    expect(rows.length).toBe(1);
    expect(rows[0].textContent).toContain("How to paint");
    unmount(app);
    target.remove();
  });

  it("shows 'No matching entries.' when search has no results", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const searchInput = target.querySelector(".kb-sidebar input") as HTMLInputElement;
    searchInput.value = "zzz";
    searchInput.dispatchEvent(new Event("input"));
    flushSync();
    expect(target.querySelector(".list-empty")?.textContent).toContain("No matching entries.");
    unmount(app);
    target.remove();
  });
});

describe("KBPage — entry selection", () => {
  it("clicking an entry shows its title and content preview", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    expect(target.querySelector(".content-title")?.textContent?.trim()).toBe("How to paint");
    expect(target.querySelector(".md-preview")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking Edit shows title input and textarea", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    const editBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "Edit",
    ) as HTMLButtonElement;
    editBtn.click();
    flushSync();
    expect(target.querySelector(".title-input")).not.toBeNull();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — save / cancel", () => {
  it("Save calls updateEntry with draft values and exits edit mode", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Save",
      ) as HTMLButtonElement
    ).click();
    await tick();
    flushSync();
    expect(store.updateEntry).toHaveBeenCalledWith("e1", {
      title: "How to paint",
      content: "# Painting\n\nUse good brushes.",
    });
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    expect(target.querySelector(".content-title")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("Cancel reverts drafts and exits edit mode without saving", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "Changed content";
    textarea.dispatchEvent(new Event("input"));
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Cancel",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(store.updateEntry).not.toHaveBeenCalled();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    expect(target.querySelector(".md-preview")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("Save shows error when title is empty", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    // Clear the title
    const titleInput = target.querySelector(".title-input") as HTMLInputElement;
    titleInput.value = "";
    titleInput.dispatchEvent(new Event("input"));
    flushSync();
    // Try to save
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Save",
      ) as HTMLButtonElement
    ).click();
    await tick();
    flushSync();
    expect(store.updateEntry).not.toHaveBeenCalled();
    expect(target.querySelector(".content-error")?.textContent).toContain("Title cannot be empty");
    // Still in edit mode
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — delete", () => {
  it("delete button shows confirmation then calls deleteEntry", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.title === "Delete entry",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(target.querySelector(".confirm-text")).not.toBeNull();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "✓",
      ) as HTMLButtonElement
    ).click();
    await tick();
    flushSync();
    expect(store.deleteEntry).toHaveBeenCalledWith("e1");
    expect(target.querySelector(".content-empty")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("cancel delete hides confirmation without deleting", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.title === "Delete entry",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "✕",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(store.deleteEntry).not.toHaveBeenCalled();
    expect(target.querySelector(".confirm-text")).toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — create new entry", () => {
  it("＋ New button calls createEntry and enters edit mode", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const newEntry = makeEntry({ id: "new1", title: "New entry", content: "" });
    const store = makeStore([], {
      createEntry: vi.fn().mockResolvedValue(newEntry),
    });
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const newBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "＋ New",
    ) as HTMLButtonElement;
    newBtn.click();
    await tick();
    // Simulate init() refresh — push the new entry so selectedEntry becomes non-null
    store.entries.push(newEntry);
    flushSync();
    expect(store.createEntry).toHaveBeenCalledWith({ title: "New entry", content: "" });
    // After create, the new entry is selected and edit mode is active
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — Media tab", () => {
  it("shows Content and Media tab buttons when entry is selected", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".content-tab")).map(t => t.textContent?.trim());
    expect(tabs).toContain("Content");
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    unmount(app);
    target.remove();
  });

  it("clicking Media tab renders MediaGallery drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ attachments: ["photo.jpg"] });
    const store = makeStore([entry]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".content-tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("switching entries resets to Content tab", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry({ id: "e1" }), makeEntry({ id: "e2", title: "Second entry" })]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    // Select first entry, switch to media
    (target.querySelectorAll(".entry-row")[0] as HTMLElement).click();
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".content-tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    // Select second entry — tab should reset to content
    (target.querySelectorAll(".entry-row")[1] as HTMLElement).click();
    flushSync();
    const activeTab = Array.from(target.querySelectorAll(".content-tab"))
      .find(t => t.classList.contains("active"));
    expect(activeTab?.textContent?.trim()).toBe("Content");
    unmount(app);
    target.remove();
  });
});

describe("KBPage — media insert button", () => {
  it("shows 📷 button when entry has attachments and Content tab is in edit mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ attachments: ["photo.jpg"] });
    const store = makeStore([entry]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("does not show 📷 button when entry has no attachments", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ attachments: [] });
    const store = makeStore([entry]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — external selection", () => {
  it("selects the entry matching selectedItemId and clears selection", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const onclearselection = vi.fn();
    const app = mount(KBPage, {
      target,
      props: { store, selectedItemId: "e1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".content-title")?.textContent?.trim()).toBe("How to paint");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(app);
    target.remove();
  });

  it("does nothing when selectedItemId doesn't match any entry", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, {
      target,
      props: { store, selectedItemId: "missing" },
    });
    flushSync();

    expect(target.querySelector(".content-empty")).not.toBeNull();

    unmount(app);
    target.remove();
  });
});
