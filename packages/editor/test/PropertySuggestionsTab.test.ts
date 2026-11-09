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

  it("shows last run counts and email error", () => {
    const store = makeSearchStore({
      searches: [makeSearch({ lastRunAt: "2026-11-08T08:00:00Z", lastRunStatus: "succeeded", lastRunNew: 3,
        lastRunDuplicates: 2, lastRunEmailError: "Brevo error 401: Key not found" })],
    });
    const t = render({ searchStore: store });
    const runs = t.querySelector(".runs")?.textContent ?? "";
    expect(runs).toContain("3 new, 2 already seen");
    expect(runs).toContain("Email not sent: Brevo error 401: Key not found");
  });

  describe("sorting", () => {
    function store() {
      return makeSearchStore({
        searches: [makeSearch({ id: "s1", name: "Zeta plots" }), makeSearch({ id: "s2", name: "Alpha houses" })],
        suggestions: [
          makeSuggestion({ id: "a", searchId: "s1", title: "Mid", price: 150000, listingUrl: "https://a.si/a" }),
          makeSuggestion({ id: "b", searchId: "s2", title: "NoPrice", price: null, listingUrl: "https://a.si/b" }),
          makeSuggestion({ id: "c", searchId: "s2", title: "Cheap", price: 50000, listingUrl: "https://a.si/c" }),
          makeSuggestion({ id: "d", searchId: "s1", title: "Pricey", price: 300000, listingUrl: "https://a.si/d" }),
        ],
      });
    }
    const titles = (t: HTMLElement) =>
      [...t.querySelectorAll('[data-testid="suggestion"] a.title')].map((a) => a.textContent);
    function sortBy(t: HTMLElement, value: string) {
      const sel = t.querySelector('[data-testid="suggestion-sort"]') as HTMLSelectElement;
      sel.value = value;
      sel.dispatchEvent(new Event("change", { bubbles: true }));
      flushSync();
    }

    it("defaults to cheapest first, unknown prices last", () => {
      const t = render({ searchStore: store() });
      expect((t.querySelector('[data-testid="suggestion-sort"]') as HTMLSelectElement).value).toBe("priceAsc");
      expect(titles(t)).toEqual(["Cheap", "Mid", "Pricey", "NoPrice"]);
    });

    it("sorts most expensive first, unknown prices still last", () => {
      const t = render({ searchStore: store() });
      sortBy(t, "priceDesc");
      expect(titles(t)).toEqual(["Pricey", "Mid", "Cheap", "NoPrice"]);
    });

    it("sorts by search name, then cheapest first", () => {
      const t = render({ searchStore: store() });
      sortBy(t, "search");
      expect(titles(t)).toEqual(["Cheap", "NoPrice", "Mid", "Pricey"]);
    });
  });

  describe("tags", () => {
    const tags = (card: Element) =>
      Object.fromEntries([...card.querySelectorAll(".tag")].map((el) => [(el as HTMLElement).dataset.tag, el.textContent?.trim()]));

    it("shows price, country and city as tags at the top of the card", () => {
      const t = render({ searchStore: makeSearchStore({
        suggestions: [makeSuggestion({ price: 150000, currency: "EUR", country: "Slovenia", city: "Novo mesto" })],
      }) });
      const card = t.querySelector('[data-testid="suggestion"]')!;
      expect(tags(card)).toEqual({ price: `${(150000).toLocaleString(undefined, { maximumFractionDigits: 0 })} EUR`, country: "Slovenia", city: "Novo mesto" });
      expect(card.querySelector(".tags")!.compareDocumentPosition(card.querySelector("a.title")!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(card.querySelector(".facts")!.textContent).not.toContain("Novo mesto");
      expect(card.querySelector(".facts")!.textContent).not.toContain("EUR");
    });

    it("falls back to the location as city and omits missing tags", () => {
      const t = render({ searchStore: makeSearchStore({
        suggestions: [makeSuggestion({ price: null, country: null, city: null, location: "Novo Mesto" })],
      }) });
      expect(tags(t.querySelector('[data-testid="suggestion"]')!)).toEqual({ city: "Novo Mesto" });
    });

    it("derives city and country from a 'town, region, country' location", () => {
      const t = render({ searchStore: makeSearchStore({
        suggestions: [makeSuggestion({ price: null, location: "Velike Brusnice, Novo mesto, Dolenjska, Slovenia" })],
      }) });
      const card = t.querySelector('[data-testid="suggestion"]')!;
      expect(tags(card)).toEqual({ country: "Slovenia", city: "Velike Brusnice" });
      expect(card.querySelector(".facts")!.textContent).toContain("Novo mesto, Dolenjska");
    });
  });
});

