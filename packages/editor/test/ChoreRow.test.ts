import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import ChoreRow from "../src/lib/components/ChoreRow.svelte";
import ChoreRowParentWrapper from "./fixtures/ChoreRowParentWrapper.svelte";

describe("ChoreRow", () => {
  it("renders emoji, name, location, and due label", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: {
        emoji: "🧹",
        name: "Sweep",
        location: "Kitchen",
        dueLabel: "Today",
        dueColor: "#4caf50",
        oncomplete: vi.fn(),
      },
    });

    expect(target.querySelector(".emoji")!.textContent).toBe("🧹");
    expect(target.querySelector(".name")!.textContent).toBe("Sweep");
    expect(target.querySelector(".location")!.textContent).toBe("Kitchen");
    expect(target.querySelector(".due")!.textContent).toBe("Today");

    unmount(comp);
    target.remove();
  });

  it("omits the location span when location is not provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete: vi.fn() },
    });

    expect(target.querySelector(".location")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("clicking the checkmark opens a completion modal, then confirm calls oncomplete with the notes", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const input = document.querySelector(".ui-modal .ui-input") as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "all done";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    (document.querySelector(".ui-modal-footer .ui-button-primary") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledWith("all done");
    expect(document.querySelector(".ui-modal")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("cancel closes the modal without calling oncomplete", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (document.querySelector(".ui-modal-footer .ui-button-secondary") as HTMLButtonElement).click();
    flushSync();

    expect(document.querySelector(".ui-modal")).toBeNull();
    expect(oncomplete).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });

  it("pressing Enter in the notes field calls oncomplete with notes value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const input = document.querySelector(".ui-modal .ui-input") as HTMLInputElement;
    input.value = "done and dusted";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();

    expect(oncomplete).toHaveBeenCalledWith("done and dusted");
    expect(document.querySelector(".ui-modal")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("pressing Escape closes the modal without calling oncomplete", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    flushSync();

    expect(document.querySelector(".ui-modal")).toBeNull();
    expect(oncomplete).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });

  it("clicking the checkmark stops propagation so a parent onclick isn't triggered", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const parentClick = vi.fn();
    const comp = mount(ChoreRowParentWrapper, {
      target,
      props: { onParentClick: parentClick },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    expect(parentClick).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });

  it("clicking cancel inside the modal doesn't bubble to a parent onclick", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const parentClick = vi.fn();
    const comp = mount(ChoreRowParentWrapper, {
      target,
      props: { onParentClick: parentClick },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (document.querySelector(".ui-modal-footer .ui-button-secondary") as HTMLButtonElement).click();
    flushSync();

    expect(parentClick).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });

  it("shows a date picker defaulting to today when marking done", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete: vi.fn() },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const dateField = document.querySelector(".ui-modal .dp-text");
    expect(dateField).not.toBeNull();
    expect(dateField!.textContent).not.toBe("");

    unmount(comp);
    target.remove();
  });

  it("confirm with the default (today) date calls oncomplete with only notes, no completedOn", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (document.querySelector(".ui-modal-footer .ui-button-primary") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledWith("");
    expect(oncomplete.mock.calls[0].length).toBe(1);

    unmount(comp);
    target.remove();
  });

  it("confirm after picking a past date calls oncomplete with notes and completedOn", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    (document.querySelector(".ui-modal .dp-field") as HTMLElement).click();
    flushSync();
    const cells = [...document.querySelectorAll(".ui-modal .dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const firstOfMonth = cells.find((c) => c.textContent === "1")!;
    firstOfMonth.click();
    flushSync();

    (document.querySelector(".ui-modal-footer .ui-button-primary") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledTimes(1);
    const [notesArg, dateArg] = oncomplete.mock.calls[0];
    expect(notesArg).toBe("");
    expect(dateArg).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    unmount(comp);
    target.remove();
  });
});
