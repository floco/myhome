import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, tick } from "svelte";
import ContactModal from "../src/lib/components/ContactModal.svelte";
import type { Contact } from "../src/lib/contactsStore.svelte";

function makeContact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "c1", name: "Metro Plumbing", companyName: null, typeId: "ctype-supplier",
    phone: null, email: null, address: null, website: null, notes: "",
    ...overrides,
  };
}

function makeStore(usage: { module: string; id: string; label: string }[] = []) {
  return {
    contacts: [makeContact()],
    loaded: true,
    loadError: null,
    createContact: vi.fn(),
    updateContact: vi.fn(),
    deleteContact: vi.fn(),
    getUsage: vi.fn().mockResolvedValue(usage),
  };
}

function makeSettingsStore() {
  return { contactTypes: [{ id: "ctype-supplier", name: "Supplier" }, { id: "ctype-contractor", name: "Contractor" }] };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("ContactModal — notes links", () => {
  it("renders a URL in notes as a clickable link when not editing", async () => {
    const contact = makeContact({ notes: "Website: https://example.com" });
    const store = { ...makeStore(), contacts: [contact] };
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ContactModal, {
      target,
      props: { contact, store, settingsStore: makeSettingsStore(), onclose: vi.fn() },
    });
    await tick();
    await tick();
    const link = target.querySelector(".md-preview a") as HTMLAnchorElement | null;
    expect(link?.getAttribute("href")).toBe("https://example.com");
    unmount(comp);
  });
});

describe("ContactModal — usage / delete protection", () => {
  it("disables delete when the contact is in use, and shows the reference", async () => {
    const store = makeStore([{ module: "works", id: "w1", label: "Fix sink" }]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ContactModal, {
      target,
      props: { contact: makeContact(), store, settingsStore: makeSettingsStore(), onclose: vi.fn() },
    });
    await tick();
    await tick();
    expect(target.textContent).toContain("Fix sink");
    const deleteButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Delete")) as HTMLButtonElement;
    expect(deleteButton.disabled).toBe(true);
    unmount(comp);
  });

  it("enables delete when the contact is not in use", async () => {
    const store = makeStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ContactModal, {
      target,
      props: { contact: makeContact(), store, settingsStore: makeSettingsStore(), onclose: vi.fn() },
    });
    await tick();
    await tick();
    expect(target.textContent).toContain("Not used anywhere yet");
    const deleteButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Delete")) as HTMLButtonElement;
    expect(deleteButton.disabled).toBe(false);
    unmount(comp);
  });
});
