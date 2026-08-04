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

  it("clicking the checkmark opens a note input, then confirm calls oncomplete with the notes", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const input = target.querySelector(".note-input") as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "all done";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledWith("all done");
    expect(target.querySelector(".note-input")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("cancel hides the note input without calling oncomplete", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".cancel-btn") as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector(".note-input")).toBeNull();
    expect(oncomplete).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });

  it("pressing Enter in note input calls oncomplete with notes value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const input = target.querySelector(".note-input") as HTMLInputElement;
    input.value = "done and dusted";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    flushSync();

    expect(oncomplete).toHaveBeenCalledWith("done and dusted");
    expect(target.querySelector(".note-input")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("pressing Escape in note input hides input without calling oncomplete", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const oncomplete = vi.fn();
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const input = target.querySelector(".note-input") as HTMLInputElement;
    input.value = "some notes";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    flushSync();

    expect(target.querySelector(".note-input")).toBeNull();
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

  it("shows a date picker defaulting to today when marking done", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Today", dueColor: "#4caf50", oncomplete: vi.fn() },
    });

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const dateField = target.querySelector(".dp-text");
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
    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
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

    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const cells = [...target.querySelectorAll(".dp-cell:not(.dp-empty)")] as HTMLButtonElement[];
    const firstOfMonth = cells.find((c) => c.textContent === "1")!;
    firstOfMonth.click();
    flushSync();

    (target.querySelector(".done-btn.confirm") as HTMLButtonElement).click();
    flushSync();

    expect(oncomplete).toHaveBeenCalledTimes(1);
    const [notesArg, dateArg] = oncomplete.mock.calls[0];
    expect(notesArg).toBe("");
    expect(dateArg).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    unmount(comp);
    target.remove();
  });
});
