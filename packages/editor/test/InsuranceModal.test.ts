import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InsuranceModal from "../src/lib/components/InsuranceModal.svelte";
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

function makeInsuranceStore(policies: InsurancePolicy[] = []) {
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
    insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }, { id: "icat-travel", name: "Travel", emoji: "✈️" }],
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

describe("InsuranceModal — create", () => {
  it("defaults includeInCosts to checked when category is Home", async () => {
    const store = makeInsuranceStore();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsuranceModal, {
      target,
      props: { policy: null, store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), onclose: vi.fn() },
    });
    flushSync();

    const costTab = Array.from(target.querySelectorAll("button.tab")).find((b) => b.textContent?.includes("Cost"));
    costTab?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const checkbox = target.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);

    unmount(comp);
  });

  it("unchecks includeInCosts when the category is changed away from Home", async () => {
    const store = makeInsuranceStore();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsuranceModal, {
      target,
      props: { policy: null, store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), onclose: vi.fn() },
    });
    flushSync();

    const categorySelect = target.querySelector(".ui-modal select") as HTMLSelectElement;
    categorySelect.value = "icat-travel";
    categorySelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const costTab = Array.from(target.querySelectorAll("button.tab")).find((b) => b.textContent?.includes("Cost"));
    costTab?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const checkbox = target.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    unmount(comp);
  });

  it("calls createPolicy with entered fields on save", async () => {
    const store = makeInsuranceStore();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsuranceModal, {
      target,
      props: { policy: null, store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), onclose: vi.fn() },
    });
    flushSync();

    const nameInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    nameInput.value = "New Policy";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const saveButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Create"));
    saveButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await Promise.resolve();

    expect(store.createPolicy).toHaveBeenCalledOnce();
    expect(store.createPolicy.mock.calls[0][0].name).toBe("New Policy");

    unmount(comp);
  });
});

describe("InsuranceModal — edit", () => {
  it("pre-fills fields from the existing policy", () => {
    const policy = makePolicy({ name: "Existing Policy" });
    const store = makeInsuranceStore([policy]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsuranceModal, {
      target,
      props: { policy, store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), onclose: vi.fn() },
    });
    flushSync();

    const nameInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    expect(nameInput.value).toBe("Existing Policy");

    unmount(comp);
  });
});
