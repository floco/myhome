import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import PropertySuggestionsTab from "../src/lib/components/PropertySuggestionsTab.svelte";
import { makeSearch, makeSuggestion } from "./fixtures/propertySearch";

function makeSearchStore(overrides: Record<string, unknown> = {}) {
  return {
    searches: [makeSearch(), makeSearch({ id: "s2", name: "Houses Ljubljana" })],
    suggestions: [makeSuggestion(), makeSuggestion({ id: "g2", searchId: "s2", title: "Big house", listingUrl: "https://b.si/2" })],
    loaded: true, loadError: null, newCount: 2,
    accept: vi.fn().mockResolvedValue({ id: "p1" }), reject: vi.fn().mockResolvedValue(undefined),
    togglePin: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

let comp: ReturnType<typeof mount> | null = null;
afterEach(() => { if (comp) unmount(comp); comp = null; document.body.innerHTML = ""; });

function render(props: Record<string, unknown>) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  comp = mount(PropertySuggestionsTab, { target, props: { onopensearches: vi.fn(), ...props } as any });
  flushSync();
  return target;
}

async function settle() {
  await new Promise((r) => setTimeout(r, 0));
  flushSync();
}

describe("PropertySuggestionsTab", () => {
  it("renders suggestions with reason and link", () => {
    const t = render({ searchStore: makeSearchStore() });
    const cards = t.querySelectorAll('[data-testid="suggestion"]');
    expect(cards.length).toBe(2);
    const link = cards[0].querySelector("a.title") as HTMLAnchorElement;
    expect(link.href).toBe("https://a.si/1");
    expect(link.target).toBe("_blank");
    expect(link.rel).toContain("noopener");
    expect(cards[0].textContent).toContain("fits");
    expect(cards[0].textContent).toContain("150,000 EUR");
  });

  it("accept calls store.accept and refreshes properties", async () => {
    const store = makeSearchStore();
    const onaccepted = vi.fn();
    const t = render({ searchStore: store, onaccepted });
    const btn = t.querySelector('[data-testid="suggestion"] button[title="Accept (add to properties)"]') as HTMLButtonElement;
    btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle();
    expect(store.accept).toHaveBeenCalledWith("g1");
    expect(onaccepted).toHaveBeenCalled();
  });

  it("shows an error when an action fails", async () => {
    const store = makeSearchStore({ reject: vi.fn().mockRejectedValue(new Error("HTTP 500")) });
    const t = render({ searchStore: store });
    (t.querySelector('button[title="Reject"]') as HTMLButtonElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle();
    expect(t.querySelector('[role="alert"]')?.textContent).toContain("HTTP 500");
  });

  it("filter by search hides others", () => {
    const t = render({ searchStore: makeSearchStore() });
    (t.querySelector(".ui-filter-button, button[title='Filters']") as HTMLButtonElement)?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    const select = document.querySelector('[data-testid="search-filter"]') as HTMLSelectElement;
    select.value = "s2";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    const titles = [...t.querySelectorAll('[data-testid="suggestion"] a.title')].map((a) => a.textContent);
    expect(titles).toEqual(["Big house"]);
  });

  it("shows the no-search empty state", () => {
    const t = render({ searchStore: makeSearchStore({ searches: [], suggestions: [] }) });
    expect(t.textContent).toContain("No search defined yet");
  });

  it("shows last run status per search", () => {
    const store = makeSearchStore({
      searches: [makeSearch({ lastRunAt: "2026-11-08T08:00:00Z", lastRunStatus: "usage_limited", lastRunError: "limit" })],
    });
    const t = render({ searchStore: store });
    expect(t.querySelector(".runs")?.textContent).toContain("usage limit reached");
  });
});
