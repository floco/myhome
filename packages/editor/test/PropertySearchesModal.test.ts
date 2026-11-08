import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import PropertySearchesModal from "../src/lib/components/PropertySearchesModal.svelte";
import { makeSearch } from "./fixtures/propertySearch";

function makeStore(searches = [makeSearch()]) {
  return {
    searches, suggestions: [], loaded: true, loadError: null, newCount: 0,
    createSearch: vi.fn().mockResolvedValue(undefined), updateSearch: vi.fn().mockResolvedValue(undefined),
    deleteSearch: vi.fn().mockResolvedValue(undefined), runNow: vi.fn().mockResolvedValue(undefined),
  };
}

let comp: ReturnType<typeof mount> | null = null;
afterEach(() => { if (comp) unmount(comp); comp = null; document.body.innerHTML = ""; });

function render(store: ReturnType<typeof makeStore>) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  comp = mount(PropertySearchesModal, { target, props: { open: true, searchStore: store, onclose: vi.fn() } as any });
  flushSync();
}

const click = (el: Element | null) => { (el as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true })); flushSync(); };
const byTestId = (id: string) => document.querySelector(`[data-testid="${id}"]`);
function setValue(id: string, value: string) {
  const el = byTestId(id) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
  el.value = value;
  el.dispatchEvent(new Event(el.tagName === "SELECT" ? "change" : "input", { bubbles: true }));
  flushSync();
}
const settle = async () => { await new Promise((r) => setTimeout(r, 0)); flushSync(); };

describe("PropertySearchesModal", () => {
  it("lists searches with a schedule summary", () => {
    render(makeStore([makeSearch({ frequency: "weekly", dayOfWeek: 3, time: "07:30" })]));
    expect(document.body.textContent).toContain("Plots");
    expect(document.body.textContent).toContain("Every Wednesday at 07:30");
  });

  it("creates a search with entered prompt", async () => {
    const store = makeStore([]);
    render(store);
    click(byTestId("new-search"));
    setValue("search-name", "Plots Novo Mesto");
    setValue("search-prompt", "land >= 800 m2 near Novo Mesto under 200k");
    setValue("search-max-results", "5");
    click(byTestId("search-save"));
    await settle();
    expect(store.createSearch).toHaveBeenCalledWith(expect.objectContaining({
      name: "Plots Novo Mesto", prompt: "land >= 800 m2 near Novo Mesto under 200k", frequency: "daily",
      time: "08:00", maxResultsPerRun: 5, maxListingAgeDays: 7, enabled: true,
    }));
  });

  it("weekly shows day-of-week select, monthly shows day-of-month", () => {
    render(makeStore([]));
    click(byTestId("new-search"));
    expect(byTestId("search-dow")).toBeNull();
    setValue("search-frequency", "weekly");
    expect(byTestId("search-dow")).not.toBeNull();
    setValue("search-frequency", "monthly");
    expect(byTestId("search-dow")).toBeNull();
    expect(byTestId("search-dom")).not.toBeNull();
  });

  it("save is disabled without name or prompt", () => {
    render(makeStore([]));
    click(byTestId("new-search"));
    expect((byTestId("search-save")!.closest("button") as HTMLButtonElement).disabled).toBe(true);
  });

  it("edits an existing search", async () => {
    const store = makeStore();
    render(store);
    click(byTestId("edit-s1"));
    setValue("search-name", "Renamed");
    click(byTestId("search-save"));
    await settle();
    expect(store.updateSearch).toHaveBeenCalledWith("s1", expect.objectContaining({ name: "Renamed" }));
  });

  it("run now calls store and shows queued note", async () => {
    const store = makeStore();
    render(store);
    click(byTestId("run-s1"));
    await settle();
    expect(store.runNow).toHaveBeenCalledWith("s1");
    expect(document.body.textContent).toContain("Queued");
  });

  it("delete asks for confirmation", async () => {
    const store = makeStore();
    render(store);
    click(byTestId("delete-s1"));
    expect(store.deleteSearch).not.toHaveBeenCalled();
    click(byTestId("confirm-delete-s1"));
    await settle();
    expect(store.deleteSearch).toHaveBeenCalledWith("s1");
  });

  it("toggling active updates the search", async () => {
    const store = makeStore();
    render(store);
    click(byTestId("toggle-s1"));
    await settle();
    expect(store.updateSearch).toHaveBeenCalledWith("s1", { enabled: false });
  });
});
