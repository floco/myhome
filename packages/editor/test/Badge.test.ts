import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Badge from "../src/lib/components/ui/Badge.svelte";

describe("ui/Badge", () => {
  it("renders the label text", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Badge, { target, props: { label: "Done", variant: "success" } });

    expect(target.querySelector(".ui-badge")!.textContent).toBe("Done");

    unmount(comp);
    target.remove();
  });

  it("applies the variant class", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Badge, { target, props: { label: "Overdue", variant: "danger" } });

    expect(target.querySelector(".ui-badge-danger")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("defaults to the neutral variant", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Badge, { target, props: { label: "Planned" } });

    expect(target.querySelector(".ui-badge-neutral")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
