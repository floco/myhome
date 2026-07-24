import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import WorksPage from "../src/lib/components/WorksPage.svelte";
import type { Work } from "../src/lib/worksStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeWork(overrides: Partial<Work> = {}): Work {
  return {
    id: "w1", title: "Fix roof leak", description: "", status: "planned",
    categoryId: null, date: "2026-06-10T12:00:00.000Z", totalCost: null,
    contactId: null, notes: "", attachments: [], placement: null,
    ...overrides,
  };
}

function makeWorksStore(works: Work[]) {
  return {
    works, loaded: true, loadError: null,
    createWork: vi.fn(), updateWork: vi.fn(), deleteWork: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(), setPlacement: vi.fn(),
  };
}

function makeSettingsStore() {
  return { workCategories: [] };
}

function makeContactsStore() {
  return { contacts: [] };
}

describe("WorksPage — external selection", () => {
  it("opens the edit modal for the work matching selectedItemId and clears selection", () => {
    const store = makeWorksStore([makeWork()]);
    const onclearselection = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(WorksPage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), selectedItemId: "w1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit work");
    const titleInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    expect(titleInput.value).toBe("Fix roof leak");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });
});

describe("WorksPage — timeline click opens modal", () => {
  it("opens the edit modal for the work whose timeline dot was clicked", () => {
    const work = makeWork({ id: "w1", title: "Fix roof leak" });
    const store = makeWorksStore([work]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(WorksPage, { target, props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() } });
    flushSync();

    const circle = target.querySelector(".chart-card-wrap circle") as SVGCircleElement;
    circle.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit work");

    unmount(comp);
  });
});
