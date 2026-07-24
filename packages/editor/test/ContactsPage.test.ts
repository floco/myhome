import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ContactsPage from "../src/lib/components/ContactsPage.svelte";
import type { Contact } from "../src/lib/contactsStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeContact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "c1", name: "Metro Plumbing", companyName: null, typeId: "ctype-supplier",
    phone: null, email: null, address: null, website: null, notes: "",
    ...overrides,
  };
}

function makeContactsStore(contacts: Contact[]) {
  return {
    contacts, loaded: true, loadError: null,
    createContact: vi.fn(), updateContact: vi.fn(), deleteContact: vi.fn(),
    getUsage: vi.fn().mockResolvedValue([]),
  };
}

function makeSettingsStore() {
  return { contactTypes: [{ id: "ctype-supplier", name: "Supplier" }, { id: "ctype-contractor", name: "Contractor" }] };
}

describe("ContactsPage", () => {
  it("shows empty state with no contacts", () => {
    const store = makeContactsStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ContactsPage, { target, props: { store, settingsStore: makeSettingsStore() } });
    flushSync();
    expect(target.textContent).toContain("No contacts yet");
    unmount(comp);
  });

  it("renders a contact row and opens the modal on click", () => {
    const store = makeContactsStore([makeContact()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ContactsPage, { target, props: { store, settingsStore: makeSettingsStore() } });
    flushSync();
    expect(target.textContent).toContain("Metro Plumbing");
    const row = Array.from(target.querySelectorAll("tr")).find((r) => r.textContent?.includes("Metro Plumbing")) as HTMLElement;
    row.click();
    flushSync();
    expect(target.textContent).toContain("Edit contact");
    unmount(comp);
  });
});
