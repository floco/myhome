import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsPropertySearch from "../src/lib/components/settings/SettingsPropertySearch.svelte";

const CONFIG = {
  retentionDays: 30, brevoApiKeySet: true, senderEmail: "home@x.si", senderName: "My Home",
  recipients: ["a@x.si", "b@x.si"], appBaseUrl: "",
};

function makeStore(overrides: Record<string, unknown> = {}) {
  return {
    loadConfig: vi.fn().mockResolvedValue({ ...CONFIG }),
    saveConfig: vi.fn().mockImplementation(async (p) => ({ ...CONFIG, ...p })),
    sendTestEmail: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

let comp: ReturnType<typeof mount> | null = null;
afterEach(() => { if (comp) unmount(comp); comp = null; document.body.replaceChildren(); });

async function render(store: ReturnType<typeof makeStore>) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  comp = mount(SettingsPropertySearch, { target, props: { searchStore: store } as any });
  await new Promise((r) => setTimeout(r, 0));
  flushSync();
  return target;
}

const q = (t: HTMLElement, id: string) => t.querySelector(`[data-testid="${id}"]`) as HTMLInputElement;
const click = (el: Element) => el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
const settle = async () => { await new Promise((r) => setTimeout(r, 0)); flushSync(); };
function type(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  el.value = value;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  flushSync();
}

describe("SettingsPropertySearch", () => {
  it("loads config and shows key-set placeholder", async () => {
    const t = await render(makeStore());
    expect(q(t, "ps-key").value).toBe("");
    expect(q(t, "ps-key").placeholder).toContain("set");
    expect((q(t, "ps-recipients") as unknown as HTMLTextAreaElement).value).toBe("a@x.si\nb@x.si");
    expect(q(t, "ps-retention").value).toBe("30");
  });

  it("save sends recipients as array and omits empty key", async () => {
    const store = makeStore();
    const t = await render(store);
    type(q(t, "ps-recipients") as unknown as HTMLTextAreaElement, "x@y.si, z@y.si\n\n w@y.si ");
    click(q(t, "ps-save").closest("button")!);
    await settle();
    const patch = store.saveConfig.mock.calls[0][0];
    expect(patch.recipients).toEqual(["x@y.si", "z@y.si", "w@y.si"]);
    expect("brevoApiKey" in patch).toBe(false);
    expect(t.textContent).toContain("Saved");
  });

  it("sends a newly typed key", async () => {
    const store = makeStore();
    const t = await render(store);
    type(q(t, "ps-key"), "xkeysib-new");
    click(q(t, "ps-save").closest("button")!);
    await settle();
    expect(store.saveConfig.mock.calls[0][0].brevoApiKey).toBe("xkeysib-new");
    expect(q(t, "ps-key").value).toBe("");
  });

  it("test email shows error message", async () => {
    const store = makeStore({ sendTestEmail: vi.fn().mockRejectedValue(new Error("Brevo error 401: Key not found")) });
    const t = await render(store);
    click(q(t, "ps-test").closest("button")!);
    await settle();
    expect(t.textContent).toContain("Key not found");
  });

  it("shows runner connection help with repo link", async () => {
    const t = await render(makeStore());
    const link = t.querySelector('a[href="https://github.com/floco/property-search-runner"]');
    expect(link).not.toBeNull();
    expect(t.textContent).toContain("MYHOME_TOKEN");
  });
});
