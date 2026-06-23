import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import Card from "../src/lib/components/ui/Card.svelte";

describe("ui/Card", () => {
  it("renders a ui-card container", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(Card, { target, props: {} });

    expect(target.querySelector(".ui-card")).not.toBeNull();

    unmount(comp);
    target.remove();
  });
});
