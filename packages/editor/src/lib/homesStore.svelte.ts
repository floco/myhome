export interface Home {
  id: string;
  name: string;
  type: "existing" | "project" | "demo";
  enabledModules: string[];
  createdAt: string;
}

const homes = $state<Home[]>([]);
let activeHomeId = $state<string | null>(null);
let loaded = $state(false);

async function loadHomes(): Promise<void> {
  const resp = await fetch("/api/homes");
  if (!resp.ok) return;
  const data: Home[] = await resp.json();
  homes.length = 0;
  for (const h of data) homes.push(h);
  loaded = true;
  if (activeHomeId === null && homes.length > 0) {
    activeHomeId = homes[0].id;
  }
}

async function createHome(name: string, type: "existing" | "project" | "demo"): Promise<Home> {
  const resp = await fetch("/api/homes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, type }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const home: Home = await resp.json();
  homes.push(home);
  activeHomeId = home.id;
  return home;
}

async function patchHome(
  id: string,
  patch: { name?: string; type?: "existing" | "project" | "demo"; enabledModules?: string[] },
): Promise<void> {
  const resp = await fetch(`/api/homes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const updated: Home = await resp.json();
  const idx = homes.findIndex((h) => h.id === id);
  if (idx >= 0) homes[idx] = updated;
}

async function deleteHome(id: string): Promise<void> {
  const resp = await fetch(`/api/homes/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const idx = homes.findIndex((h) => h.id === id);
  if (idx >= 0) homes.splice(idx, 1);
  if (activeHomeId === id) {
    activeHomeId = homes[0]?.id ?? null;
  }
}

function setActiveHomeId(id: string): void {
  activeHomeId = id;
}

function _reset(): void {
  homes.length = 0;
  activeHomeId = null;
  loaded = false;
}

export const homesStore = {
  get homes() { return homes; },
  get activeHomeId() { return activeHomeId; },
  get activeHome() { return homes.find((h) => h.id === activeHomeId) ?? null; },
  get loaded() { return loaded; },
  loadHomes,
  createHome,
  patchHome,
  deleteHome,
  setActiveHomeId,
  _reset,
};
