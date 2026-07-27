import { describe, it, expect } from "vitest";
import { mount, unmount, createRawSnippet } from "svelte";
import StatTile from "../src/lib/components/ui/StatTile.svelte";

describe("ui/StatTile", () => {
  it("renders the value and label", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 128, label: "Items" } });

    expect(target.querySelector(".ui-stat-value")!.textContent).toBe("128");
    expect(target.querySelector(".ui-stat-label")!.textContent).toBe("Items");

    unmount(comp);
    target.remove();
  });

  it("accepts a string value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: "18.6k km", label: "Distance" } });

    expect(target.querySelector(".ui-stat-value")!.textContent).toBe("18.6k km");

    unmount(comp);
    target.remove();
  });

  it("applies a danger variant class to the value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 3, label: "Overdue", variant: "danger" } });

    expect(target.querySelector(".ui-stat-value")!.classList.contains("danger")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("applies a success variant class to the value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: "33%", label: "On track", variant: "success" } });

    expect(target.querySelector(".ui-stat-value")!.classList.contains("success")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("applies a warning variant class to the value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 2, label: "Low stock", variant: "warning" } });

    expect(target.querySelector(".ui-stat-value")!.classList.contains("warning")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("has no variant class by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(StatTile, { target, props: { value: 5, label: "Active" } });

    const el = target.querySelector(".ui-stat-value")!;
    expect(el.classList.contains("danger")).toBe(false);
    expect(el.classList.contains("success")).toBe(false);
    expect(el.classList.contains("warning")).toBe(false);

    unmount(comp);
    target.remove();
  });

  it("renders valueContent instead of the plain value when provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const valueContent = createRawSnippet(() => ({
      render: () => `<span class="custom-value">1,234 € <b class="up">▲2%</b></span>`,
    }));
    const comp = mount(StatTile, { target, props: { value: "1,234 €", label: "Last year", valueContent } });

    expect(target.querySelector(".custom-value")).not.toBeNull();
    expect(target.querySelector(".up")!.textContent).toBe("▲2%");

    unmount(comp);
    target.remove();
  });
});
