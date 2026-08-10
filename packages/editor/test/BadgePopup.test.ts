import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import BadgePopup from "../src/lib/components/BadgePopup.svelte";
import type { Chore, Assignment } from "../src/lib/choreStore.svelte";

function makeChore(overrides: Partial<Chore> = {}): Chore {
  return {
    id: "c1", donetickId: null, name: "🧹 Sweep", emoji: "🧹",
    periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {},
    scheduleFromDue: false, nextDueDate: "2027-01-01T00:00:00Z", description: "", attachments: [],
    ...overrides,
  };
}

function makeAssignment(overrides: Partial<Assignment> = {}): Assignment {
  return {
    id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 2 },
    nextDueDate: "2027-01-01T00:00:00Z", label: null,
    ...overrides,
  };
}

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

function baseProps(overrides: Record<string, unknown> = {}) {
  return {
    chore: makeChore(),
    assignment: makeAssignment(),
    screenX: 10,
    screenY: 10,
    oncomplete: vi.fn(),
    oncompleteall: vi.fn(),
    onremove: vi.fn(),
    onclose: vi.fn(),
    onlabelchange: vi.fn(),
    ...overrides,
  };
}

describe("BadgePopup — label", () => {
  it("pre-fills the label input from the assignment's existing label", () => {
    const el = target();
    const comp = mount(BadgePopup, { target: el, props: baseProps({ assignment: makeAssignment({ label: "Side A" }) }) });
    flushSync();
    expect((el.querySelector(".popup-label-input") as HTMLInputElement).value).toBe("Side A");
    unmount(comp);
    el.remove();
  });

  it("shows an empty label input when the assignment has no label", () => {
    const el = target();
    const comp = mount(BadgePopup, { target: el, props: baseProps() });
    flushSync();
    expect((el.querySelector(".popup-label-input") as HTMLInputElement).value).toBe("");
    unmount(comp);
    el.remove();
  });

  it("calls onlabelchange with the trimmed value on blur when the label changed", () => {
    const el = target();
    const onlabelchange = vi.fn();
    const comp = mount(BadgePopup, { target: el, props: baseProps({ onlabelchange }) });
    flushSync();
    const input = el.querySelector(".popup-label-input") as HTMLInputElement;
    input.value = "  Window 1  ";
    input.dispatchEvent(new Event("blur"));
    expect(onlabelchange).toHaveBeenCalledWith("Window 1");
    unmount(comp);
    el.remove();
  });

  it("does not call onlabelchange when the value is unchanged on blur", () => {
    const el = target();
    const onlabelchange = vi.fn();
    const comp = mount(BadgePopup, {
      target: el,
      props: baseProps({ assignment: makeAssignment({ label: "Window 1" }), onlabelchange }),
    });
    flushSync();
    const input = el.querySelector(".popup-label-input") as HTMLInputElement;
    input.value = "Window 1";
    input.dispatchEvent(new Event("blur"));
    expect(onlabelchange).not.toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});

describe("BadgePopup — existing behavior", () => {
  it("shows the chore name", () => {
    const el = target();
    const comp = mount(BadgePopup, { target: el, props: baseProps() });
    flushSync();
    expect(el.querySelector(".popup-name")?.textContent).toBe("🧹 Sweep");
    unmount(comp);
    el.remove();
  });

  it("calls oncompleteall when 'All done' is clicked", () => {
    const el = target();
    const oncompleteall = vi.fn();
    const comp = mount(BadgePopup, { target: el, props: baseProps({ oncompleteall }) });
    flushSync();
    (Array.from(el.querySelectorAll("button")).find((b) => b.textContent?.includes("All done")) as HTMLButtonElement).click();
    expect(oncompleteall).toHaveBeenCalledOnce();
    unmount(comp);
    el.remove();
  });
});
