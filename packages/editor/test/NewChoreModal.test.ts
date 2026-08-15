import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import NewChoreModal from "../src/lib/components/NewChoreModal.svelte";

function makeStore(overrides = {}) {
  return {
    createChore: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("NewChoreModal", () => {
  it("quick-add parses a recurring phrase and pre-fills the name + schedule category", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(NewChoreModal, { target, props: { open: true, store, onclose: vi.fn() } });
    flushSync();

    const quickAdd = target.querySelector("#chore-quickadd") as HTMLInputElement;
    quickAdd.value = "Change water filter every 6 months";
    quickAdd.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const parseBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Parse") as HTMLButtonElement;
    parseBtn.click();
    flushSync();

    const nameInput = target.querySelector("#chore-name") as HTMLInputElement;
    expect(nameInput.value).toBe("Change water filter");
    const categorySelect = target.querySelector("#se-category") as HTMLSelectElement;
    expect(categorySelect.value).toBe("interval");

    unmount(app);
  });

  it("Create calls createChore with the parsed schedule and default first-due date", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const onclose = vi.fn();
    const app = mount(NewChoreModal, { target, props: { open: true, store, onclose } });
    flushSync();

    const nameInput = target.querySelector("#chore-name") as HTMLInputElement;
    nameInput.value = "Sweep";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const createBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Create") as HTMLButtonElement;
    createBtn.click();
    await tick();

    expect(store.createChore).toHaveBeenCalledWith(expect.objectContaining({
      name: "Sweep",
      frequencyType: "interval",
      frequency: 30,
      frequencyMetadata: { unit: "days" },
      periodDays: 30,
    }));
    expect(onclose).toHaveBeenCalledOnce();

    unmount(app);
  });

  it("uses the shared DatePicker for the first-due date instead of a native date input", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(NewChoreModal, { target, props: { open: true, store, onclose: vi.fn() } });
    flushSync();

    expect(target.querySelector('input[type="date"]')).toBeNull();
    expect(target.querySelector(".dp-field")).not.toBeNull();

    unmount(app);
  });

  it("defaults to the 'schedule from completion date' radio and selecting the due-date one sends scheduleFromDue: true", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(NewChoreModal, { target, props: { open: true, store, onclose: vi.fn() } });
    flushSync();

    expect(target.querySelector('input[type="checkbox"]#sfd')).toBeNull();
    const dueRadio = target.querySelector("#new-sfd-due") as HTMLInputElement;
    const completionRadio = target.querySelector("#new-sfd-completion") as HTMLInputElement;
    expect(completionRadio.checked).toBe(true);
    expect(dueRadio.checked).toBe(false);

    const nameInput = target.querySelector("#chore-name") as HTMLInputElement;
    nameInput.value = "Sweep";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    dueRadio.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const createBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Create") as HTMLButtonElement;
    createBtn.click();
    await tick();

    expect(store.createChore).toHaveBeenCalledWith(expect.objectContaining({ scheduleFromDue: true }));

    unmount(app);
  });

  it("shows the emoji picker just before the name field on the same row", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(NewChoreModal, { target, props: { open: true, store, onclose: vi.fn() } });
    flushSync();

    const row = target.querySelector(".name-emoji-row");
    expect(row).not.toBeNull();
    const [emojiField, nameField] = Array.from(row!.children);
    expect(emojiField.querySelector(".ep-trigger")).not.toBeNull();
    expect(nameField.querySelector("#chore-name")).not.toBeNull();

    unmount(app);
  });

  it("Create is disabled when the schedule is invalid (e.g. Weekly-on-days with no day selected)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(NewChoreModal, { target, props: { open: true, store, onclose: vi.fn() } });
    flushSync();

    const nameInput = target.querySelector("#chore-name") as HTMLInputElement;
    nameInput.value = "Take out trash";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const categorySelect = target.querySelector("#se-category") as HTMLSelectElement;
    categorySelect.value = "days_of_the_week";
    categorySelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const createBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Create") as HTMLButtonElement;
    expect(createBtn.disabled).toBe(true);

    unmount(app);
  });
});
