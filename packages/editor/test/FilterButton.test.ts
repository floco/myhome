import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import FilterButton from "../src/lib/components/ui/FilterButton.svelte";

describe("ui/FilterButton", () => {
  it("calls onclick when clicked", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onclick = vi.fn();
    const comp = mount(FilterButton, { target, props: { onclick, title: "Filters" } });

    target.querySelector("button")!.click();
    expect(onclick).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("shows no badge by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(FilterButton, { target, props: { onclick: () => {}, title: "Filters" } });

    expect(target.querySelector(".badge")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("shows a badge when active", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(FilterButton, { target, props: { onclick: () => {}, title: "Filters", active: true } });

    expect(target.querySelector(".badge")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("sets title and aria-label for accessibility", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(FilterButton, { target, props: { onclick: () => {}, title: "Filters" } });

    const btn = target.querySelector("button")!;
    expect(btn.getAttribute("title")).toBe("Filters");
    expect(btn.getAttribute("aria-label")).toBe("Filters");

    unmount(comp);
    target.remove();
  });
});
