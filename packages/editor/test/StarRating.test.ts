import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import StarRating from "../src/lib/components/ui/StarRating.svelte";

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("StarRating", () => {
  it("renders 3 filled and 2 empty stars for a score of 3", () => {
    const el = target();
    const comp = mount(StarRating, { target: el, props: { score: 3 } });
    flushSync();
    const stars = Array.from(el.querySelectorAll(".star"));
    expect(stars.length).toBe(5);
    expect(stars.filter((s) => s.classList.contains("filled")).length).toBe(3);
    expect(stars[0].textContent).toBe("★");
    expect(stars[4].textContent).toBe("☆");
    unmount(comp);
    el.remove();
  });

  it("renders all empty stars for a null score", () => {
    const el = target();
    const comp = mount(StarRating, { target: el, props: { score: null } });
    flushSync();
    const stars = Array.from(el.querySelectorAll(".star"));
    expect(stars.every((s) => !s.classList.contains("filled"))).toBe(true);
    unmount(comp);
    el.remove();
  });

  it("non-interactive renders no click handlers (plain spans, no buttons)", () => {
    const el = target();
    const comp = mount(StarRating, { target: el, props: { score: 2 } });
    flushSync();
    expect(el.querySelectorAll(".star-btn").length).toBe(0);
    expect(el.querySelectorAll(".star").length).toBe(5);
    unmount(comp);
    el.remove();
  });

  it("interactive clicks call onselect with the clicked value", () => {
    const onselect = vi.fn();
    const el = target();
    const comp = mount(StarRating, { target: el, props: { score: 2, interactive: true, onselect } });
    flushSync();
    const buttons = Array.from(el.querySelectorAll(".star-btn"));
    expect(buttons.length).toBe(5);
    (buttons[3] as HTMLButtonElement).click();
    expect(onselect).toHaveBeenCalledWith(4);
    unmount(comp);
    el.remove();
  });
});
