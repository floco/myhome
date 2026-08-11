import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import FloorSwitcher from "../src/lib/components/FloorSwitcher.svelte";

describe("FloorSwitcher — compact mobile trigger", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("renders an icon alongside the floor-name label in the compact trigger", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(FloorSwitcher, {
      target,
      props: {
        floors: [{ id: "f1", name: "Ground Floor", order: 0, walls: [], openings: [], rooms: [] }],
        currentFloorId: "f1",
        onswitchfloor: () => {},
        compact: true,
      },
    });
    flushSync();

    const btn = target.querySelector(".compact-btn") as HTMLButtonElement;
    expect(btn.querySelector(".compact-icon")?.textContent).toBe("🏢");
    expect(btn.querySelector(".compact-label")?.textContent).toBe("Ground Floor");
  });
});
