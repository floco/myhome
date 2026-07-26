// packages/editor/src/lib/insuranceStore.svelte.ts

export interface InsurancePolicy {
  id: string;
  name: string;
  categoryId: string;
  contactId: string | null;
  policyNumber: string | null;
  coverageSummary: string;
  conditionsUrl: string | null;
  startDate: string | null;
  endDate: string | null;
  premiumAmount: number | null;
  premiumFrequency: "monthly" | "quarterly" | "annual" | "other";
  includeInCosts: boolean;
  alternatives: string;
  notes: string;
  attachments: string[];
  linkedCostEntryId: string | null;
}

export interface InsuranceDocument {
  version: number;
  policies: InsurancePolicy[];
}

export function createInsuranceStore(getHomeId: () => string | null = () => null) {
  const policies = $state<InsurancePolicy[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/insurance`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: InsuranceDocument = await resp.json();
      policies.length = 0;
      for (const p of doc.policies) policies.push(p);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createPolicy(
    data: Omit<InsurancePolicy, "id" | "attachments" | "linkedCostEntryId">
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/insurance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updatePolicy(
    id: string,
    patch: Partial<Omit<InsurancePolicy, "id" | "attachments" | "linkedCostEntryId">>
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deletePolicy(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}/attachments`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(id: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}/attachments/${filename}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get policies() { return policies as InsurancePolicy[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createPolicy,
    updatePolicy,
    deletePolicy,
    uploadAttachment,
    deleteAttachment,
    reload: init,
  };
}
