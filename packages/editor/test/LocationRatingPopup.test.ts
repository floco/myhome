import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationRatingPopup from "../src/lib/components/LocationRatingPopup.svelte";

const location = { id: "l1", name: "Nantes", emoji: "🇫🇷" };
const criterion = { id: "c1", name: "Cost of Living", description: "", weight: "medium" as const };

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("LocationRatingPopup", () => {
  it("pre-fills score and note from the existing rating", () => {
    const el = target();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: {
        location, criterion,
        rating: { locationId: "l1", criterionId: "c1", score: 3, note: "decent" },
        anchorX: 10, anchorY: 10,
        onsave: vi.fn(), onclose: vi.fn(),
      },
    });
    flushSync();
    expect(document.querySelectorAll(".star-btn.filled").length).toBe(3);
    expect((document.querySelector(".note-textarea") as HTMLTextAreaElement).value).toBe("decent");
    unmount(comp);
    el.remove();
  });

  it("selecting a score and saving calls onsave with the score and note", () => {
    const el = target();
    const onsave = vi.fn();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: { location, criterion, rating: null, anchorX: 0, anchorY: 0, onsave, onclose: vi.fn() },
    });
    flushSync();
    const buttons = Array.from(document.querySelectorAll(".star-btn"));
    (buttons[3] as HTMLButtonElement).click(); // score 4
    const textarea = document.querySelector(".note-textarea") as HTMLTextAreaElement;
    textarea.value = "Great fit";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    (document.querySelector(".save-btn") as HTMLButtonElement).click();
    expect(onsave).toHaveBeenCalledWith(4, "Great fit");
    unmount(comp);
    el.remove();
  });

  it("clear calls onsave with null score and empty note", () => {
    const el = target();
    const onsave = vi.fn();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: {
        location, criterion,
        rating: { locationId: "l1", criterionId: "c1", score: 5, note: "x" },
        anchorX: 0, anchorY: 0, onsave, onclose: vi.fn(),
      },
    });
    flushSync();
    (document.querySelector(".clear-btn") as HTMLButtonElement).click();
    expect(onsave).toHaveBeenCalledWith(null, "");
    unmount(comp);
    el.remove();
  });

  it("Escape key closes the popup", () => {
    const el = target();
    const onclose = vi.fn();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: { location, criterion, rating: null, anchorX: 0, anchorY: 0, onsave: vi.fn(), onclose },
    });
    flushSync();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(onclose).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});
