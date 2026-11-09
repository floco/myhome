import type { PropertySearch, PropertySuggestion } from "../../src/lib/propertySearchStore.svelte";

export function makeSearch(o: Partial<PropertySearch> = {}): PropertySearch {
  return {
    id: "s1", name: "Plots", prompt: "land", enabled: true, frequency: "daily", time: "08:00",
    dayOfWeek: 1, dayOfMonth: 1, maxResultsPerRun: 10, maxListingAgeDays: 7, createdAt: "2026-11-01T00:00:00Z",
    runRequestedAt: null, lastRunAt: null, lastRunStatus: null, lastRunError: null, ...o,
  };
}

export function makeSuggestion(o: Partial<PropertySuggestion> = {}): PropertySuggestion {
  return {
    id: "g1", searchId: "s1", runId: "r1", title: "Nice plot", type: "land", price: 150000, currency: "EUR",
    landSize: 820, builtSize: null, bedrooms: null, bathrooms: null, location: "Novo Mesto", country: null, region: null, city: null,
    sourceSite: "nepremicnine.net", listingUrl: "https://a.si/1", imageUrl: null, publishedAt: "2026-11-07",
    reason: "fits", status: "new", createdAt: "2026-11-08T08:00:00Z", acceptedPropertyId: null, ...o,
  };
}
