import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import KBTree from "../src/lib/components/ui/KBTree.svelte";
import type { KBEntry, KBFolder } from "../src/lib/kbStore.svelte";

function makeFolder(overrides: Partial<KBFolder> = {}): KBFolder {
  return { id: "f1", name: "Appliances", parentId: null, ...overrides };
}

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1", title: "How to paint", content: "", createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z", attachments: [], folderId: null, ...overrides,
  };
}

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    folders: [] as KBFolder[],
    entries: [] as KBEntry[],
    selectedId: null,
    searchQuery: "",
    collapsedIds: new Set<string>(),
    renamingFolderId: null,
    dragging: null,
    onselectentry: vi.fn(),
    ontogglefolder: vi.fn(),
    oncreatesubfolder: vi.fn(),
    oncreateentryin: vi.fn(),
    onstartrename: vi.fn(),
    oncommitrename: vi.fn(),
    oncancelrename: vi.fn(),
    ondeletefolder: vi.fn(),
    onstartdrag: vi.fn(),
    onenddrag: vi.fn(),
    ondropon: vi.fn(),
    ...overrides,
  };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = baseProps(overrides);
  const comp = mount(KBTree, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("KBTree — rendering", () => {
  it("renders root-level folders and entries", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", title: "Wifi password", folderId: null })],
    });
    expect(target.querySelector(".folder-name")?.textContent).toBe("Manuals");
    expect(target.querySelector(".entry-title")?.textContent).toBe("Wifi password");
    unmount(comp);
    target.remove();
  });

  it("shows 'No entries yet.' when the tree is empty", () => {
    const { target, comp } = setup();
    expect(target.querySelector(".list-empty")?.textContent).toContain("No entries yet.");
    unmount(comp);
    target.remove();
  });

  it("nests entries under their folder, not at the root", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", title: "Nested entry", folderId: "f1" })],
    });
    const allEntryRows = target.querySelectorAll(".entry-row");
    expect(allEntryRows.length).toBe(1);
    expect(allEntryRows[0].textContent).toContain("Nested entry");
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — expand/collapse", () => {
  it("clicking the disclosure calls ontogglefolder with the folder id", () => {
    const ontogglefolder = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      ontogglefolder,
    });
    (target.querySelector(".disclosure") as HTMLElement).click();
    expect(ontogglefolder).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("hides nested entries when the folder id is in collapsedIds", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", folderId: "f1" })],
      collapsedIds: new Set(["f1"]),
    });
    expect(target.querySelector(".entry-row")).toBeNull();
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — search filter", () => {
  it("hides folders with no matching descendants", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" }), makeFolder({ id: "f2", name: "Warranties" })],
      entries: [makeEntry({ id: "e1", title: "Wifi password", folderId: "f1" })],
      searchQuery: "wifi",
    });
    const names = Array.from(target.querySelectorAll(".folder-name")).map((n) => n.textContent);
    expect(names).toEqual(["Manuals"]);
    unmount(comp);
    target.remove();
  });

  it("auto-expands a folder containing a match even if collapsed", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Manuals" })],
      entries: [makeEntry({ id: "e1", title: "Wifi password", folderId: "f1" })],
      collapsedIds: new Set(["f1"]),
      searchQuery: "wifi",
    });
    expect(target.querySelector(".entry-title")?.textContent).toBe("Wifi password");
    unmount(comp);
    target.remove();
  });

  it("shows 'No matching entries.' when nothing matches", () => {
    const { target, comp } = setup({
      entries: [makeEntry({ id: "e1", title: "Wifi password" })],
      searchQuery: "zzz",
    });
    expect(target.querySelector(".list-empty")?.textContent).toContain("No matching entries.");
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — folder context menu", () => {
  function openMenu(target: HTMLElement) {
    (target.querySelector(".menu-trigger") as HTMLElement).click();
    flushSync();
  }

  it("New subfolder calls oncreatesubfolder with the folder id", () => {
    const oncreatesubfolder = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], oncreatesubfolder });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "New subfolder") as HTMLButtonElement;
    btn.click();
    expect(oncreatesubfolder).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("New entry here calls oncreateentryin with the folder id", () => {
    const oncreateentryin = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], oncreateentryin });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "New entry here") as HTMLButtonElement;
    btn.click();
    expect(oncreateentryin).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("Rename calls onstartrename with the folder id", () => {
    const onstartrename = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], onstartrename });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "Rename") as HTMLButtonElement;
    btn.click();
    expect(onstartrename).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("Delete is disabled when the folder has entries", () => {
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1" })],
      entries: [makeEntry({ id: "e1", folderId: "f1" })],
    });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "Delete") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    unmount(comp);
    target.remove();
  });

  it("Delete calls ondeletefolder when the folder is empty", () => {
    const ondeletefolder = vi.fn();
    const { target, comp } = setup({ folders: [makeFolder({ id: "f1" })], ondeletefolder });
    openMenu(target);
    const btn = Array.from(target.querySelectorAll(".folder-menu button"))
      .find((b) => b.textContent === "Delete") as HTMLButtonElement;
    btn.click();
    expect(ondeletefolder).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — inline rename", () => {
  it("shows a text input for the folder being renamed and commits on Enter", () => {
    const oncommitrename = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Old name" })],
      renamingFolderId: "f1",
      oncommitrename,
    });
    const input = target.querySelector(".rename-input") as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "New name";
    input.dispatchEvent(new Event("input"));
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(oncommitrename).toHaveBeenCalledWith("f1", "New name");
    unmount(comp);
    target.remove();
  });

  it("Escape cancels the rename", () => {
    const oncancelrename = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1", name: "Old name" })],
      renamingFolderId: "f1",
      oncancelrename,
    });
    const input = target.querySelector(".rename-input") as HTMLInputElement;
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(oncancelrename).toHaveBeenCalled();
    unmount(comp);
    target.remove();
  });
});

describe("KBTree — drag and drop", () => {
  it("dragstart on an entry calls onstartdrag with kind entry", () => {
    const onstartdrag = vi.fn();
    const { target, comp } = setup({ entries: [makeEntry({ id: "e1" })], onstartdrag });
    (target.querySelector(".entry-row") as HTMLElement).dispatchEvent(new Event("dragstart"));
    expect(onstartdrag).toHaveBeenCalledWith("entry", "e1");
    unmount(comp);
    target.remove();
  });

  it("dropping on a folder calls ondropon with the folder id", () => {
    const ondropon = vi.fn();
    const { target, comp } = setup({
      folders: [makeFolder({ id: "f1" })],
      dragging: { kind: "entry", id: "e1" },
      ondropon,
    });
    (target.querySelector(".folder-row") as HTMLElement).dispatchEvent(new Event("drop"));
    expect(ondropon).toHaveBeenCalledWith("f1");
    unmount(comp);
    target.remove();
  });

  it("does not allow dropping a folder onto its own descendant", () => {
    const ondropon = vi.fn();
    const { target, comp } = setup({
      folders: [
        makeFolder({ id: "f1", name: "Parent" }),
        makeFolder({ id: "f2", name: "Child", parentId: "f1" }),
      ],
      dragging: { kind: "folder", id: "f1" },
      ondropon,
    });
    const rows = target.querySelectorAll(".folder-row");
    (rows[1] as HTMLElement).dispatchEvent(new Event("drop"));
    expect(ondropon).not.toHaveBeenCalled();
    unmount(comp);
    target.remove();
  });

  it("shows the root drop zone only while dragging", () => {
    const { target: idle, comp: idleComp } = setup();
    expect(idle.querySelector(".root-dropzone")).toBeNull();
    unmount(idleComp);
    idle.remove();

    const { target, comp } = setup({ dragging: { kind: "entry", id: "e1" } });
    expect(target.querySelector(".root-dropzone")).not.toBeNull();
    unmount(comp);
    target.remove();
  });

  it("dropping on the root zone calls ondropon with null", () => {
    const ondropon = vi.fn();
    const { target, comp } = setup({ dragging: { kind: "entry", id: "e1" }, ondropon });
    (target.querySelector(".root-dropzone") as HTMLElement).dispatchEvent(new Event("drop"));
    expect(ondropon).toHaveBeenCalledWith(null);
    unmount(comp);
    target.remove();
  });
});
