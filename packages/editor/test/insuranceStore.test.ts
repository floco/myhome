import { describe, it, expect, afterEach, vi } from "vitest";
import { createInsuranceStore } from "../src/lib/insuranceStore.svelte";
import type { InsurancePolicy } from "../src/lib/insuranceStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function makePolicy(overrides: Partial<InsurancePolicy> = {}): InsurancePolicy {
  return {
    id: "ins1", name: "Home Insurance", categoryId: "icat-home", contactId: null,
    policyNumber: null, coverageSummary: "", conditionsUrl: null, startDate: null, endDate: null,
    premiumAmount: 45, premiumFrequency: "monthly", includeInCosts: true,
    alternatives: "", notes: "", attachments: [], linkedCostEntryId: "c1",
    ...overrides,
  };
}

const emptyDoc = { version: 1, policies: [] };

describe("insuranceStore — init", () => {
  it("loads policies from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, policies: [makePolicy()] }));
    const store = createInsuranceStore(getHomeId);
    await tick();
    expect(store.policies.length).toBe(1);
    expect(store.policies[0].id).toBe("ins1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createInsuranceStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("insuranceStore — createPolicy", () => {
  it("posts to /api/homes/{homeId}/insurance and refreshes", async () => {
    const created = makePolicy({ id: "ins2", name: "Travel Insurance" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, policies: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore(getHomeId);
    await tick();
    await store.createPolicy({
      name: "Travel Insurance", categoryId: "icat-travel", contactId: null, policyNumber: null,
      coverageSummary: "", conditionsUrl: null, startDate: null, endDate: null,
      premiumAmount: null, premiumFrequency: "annual", includeInCosts: false, alternatives: "", notes: "",
    });
    await tick();
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/insurance`);
    expect(fetchFn.mock.calls[1][1].method).toBe("POST");
    expect(store.policies.length).toBe(1);
  });
});

describe("insuranceStore — deletePolicy", () => {
  it("calls DELETE /api/homes/{homeId}/insurance/{id}", async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore(getHomeId);
    await tick();
    await store.deletePolicy("ins1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/insurance/ins1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("DELETE");
  });
});

describe("insuranceStore — uploadAttachment", () => {
  it("posts multipart form to /api/homes/{homeId}/attachments/insurance/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ filename: "policy.pdf" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore(getHomeId);
    await tick();
    const file = new File(["%PDF"], "policy.pdf", { type: "application/pdf" });
    const filename = await store.uploadAttachment("ins1", file);
    expect(filename).toBe("policy.pdf");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/attachments/insurance/ins1`);
  });
});
