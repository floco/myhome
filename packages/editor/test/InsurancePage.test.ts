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
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(), reload: vi.fn(),
  };
}

function makeSettingsStore() {
  return {
    costCategories: [], inventoryCategories: [], workCategories: [], contactTypes: [],
    consumableUnits: [], consumableCategories: [],
    insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }],
    notificationSettings: {
      enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
      haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
    },
    loaded: true, loadError: null,
    updateCostCategories: vi.fn(), updateInventoryCategories: vi.fn(), updateWorkCategories: vi.fn(),
    updateContactTypes: vi.fn(), updateConsumableUnits: vi.fn(), updateConsumableCategories: vi.fn(),
    updateInsuranceCategories: vi.fn(), updateNotificationSettings: vi.fn(), placeCostCategory: vi.fn(),
    reload: vi.fn(),
  };
}

function makeContactsStore() {
  return {
    contacts: [], loaded: true, loadError: null,
    createContact: vi.fn(), updateContact: vi.fn(), deleteContact: vi.fn(), getUsage: vi.fn(), reload: vi.fn(),
  };
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

    const addButton = target.querySelector('button[title="Add policy"]');
    addButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toContain("New policy");

    unmount(comp);
  });
});

describe("InsurancePage — responsive columns", () => {
  it("hides category/provider at tablet and endDate at mobile", () => {
    const store = makeInsuranceStore([makePolicy()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InsurancePage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, category, provider, premium, endDate
    expect(headers[2].classList.contains("col-hide-tablet")).toBe(true); // category
    expect(headers[3].classList.contains("col-hide-tablet")).toBe(true); // provider
    expect(headers[5].classList.contains("col-hide-mobile")).toBe(true); // endDate
    expect(headers[4].classList.contains("col-hide-tablet")).toBe(false); // premium always visible

    unmount(comp);
  });
});
