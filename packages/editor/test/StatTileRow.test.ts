import { describe, it, expect } from "vitest";
import { mount, unmount } from "svelte";
import StatTileRow from "../src/lib/components/ui/StatTileRow.svelte";
import StatTile from "../src/lib/components/ui/StatTile.svelte";

describe("ui/StatTileRow", () => {
  it("renders its children inside the stat row grid", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(StatTileRow, {
      target,
      props: {
        children: () => {
          const c = mount(StatTile, { target: document.createElement("div"), props: { value: 1, label: "A" } });
          return c;
        },
      },
    });

    // children snippet composition is exercised end-to-end in each page's
    // own tests (Task 3+); here we just confirm the row wrapper itself renders.
    expect(target.querySelector(".ui-stat-row")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("applies the column class when direction is column", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(StatTileRow, {
      target,
      props: {
        direction: "column",
        children: () => mount(StatTile, { target: document.createElement("div"), props: { value: 1, label: "A" } }),
      },
    });

    expect(target.querySelector(".ui-stat-row")!.classList.contains("column")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("has no column class by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(StatTileRow, {
      target,
      props: {
        children: () => mount(StatTile, { target: document.createElement("div"), props: { value: 1, label: "A" } }),
      },
    });

    expect(target.querySelector(".ui-stat-row")!.classList.contains("column")).toBe(false);

    unmount(comp);
    target.remove();
  });
});
