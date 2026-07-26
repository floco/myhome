import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InsurancePage from "../src/lib/components/InsurancePage.svelte";
import type { InsurancePolicy } from "../src/lib/insuranceStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makePolicy(overrides: Partial<InsurancePolicy> = {}): InsurancePolicy {
  return {
    id: "ins1", name: "Home Insurance", categoryId: "icat-home", contactId: null,
    policyNumber: null, coverageSummary: "", conditionsUrl: null, startDate: null, endDate: null,
    premiumAmount: 45, premiumFrequency: "monthly", includeInCosts: true,
    alternatives: "", notes: "", attachments: [], linkedCostEntryId: "c1",
    ...overrides,
  };
}

function makeInsuranceStore(policies: InsurancePolicy[]) {
  return {
    policies, loaded: true, loadError: null,
    createPolicy: vi.fn(), updatePolicy: vi.fn(), deletePolicy: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(),
  };
}

function makeSettingsStore() {
  return { insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }] };
}

function makeContactsStore() {
  return { contacts: [] };
}

describe("InsurancePage — list rendering", () => {
  it("renders a row for each policy", () => {
    const store = makeInsuranceStore([makePolicy(), makePolicy({ id: "ins2", name: "Travel Insurance", categoryId: "icat-travel", includeInCosts: false })]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsurancePage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    expect(target.textContent).toContain("Home Insurance");
    expect(target.textContent).toContain("Travel Insurance");

    unmount(comp);
  });
});

describe("InsurancePage — add policy", () => {
  it("opens the create modal when Add policy is clicked", () => {
    const store = makeInsuranceStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsurancePage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    const addButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Add policy"));
    addButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toContain("New policy");

    unmount(comp);
  });
});
