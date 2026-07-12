import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomesSwitcher from "../src/lib/components/HomesSwitcher.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

afterEach(() => {
  vi.restoreAllMocks();
  homesStore._reset();
});

describe("HomesSwitcher — demo home icon", () => {
  it("shows a distinct icon for demo-type homes in the dropdown", async () => {
    homesStore.homes.push(
      { id: "h1", name: "Real House", type: "existing", enabledModules: [], createdAt: "" },
      { id: "h2", name: "Demo House", type: "demo", enabledModules: [], createdAt: "" },
    );
    homesStore.setActiveHomeId("h1");

    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomesSwitcher, { target, props: { expanded: true } });
    await tick();
    flushSync();

    const current = target.querySelector(".current") as HTMLButtonElement;
    current.click();
    await tick();
    flushSync();

    const items = Array.from(target.querySelectorAll(".home-item"));
    const demoItem = items.find((el) => el.textContent?.includes("Demo House"));
    const existingItem = items.find((el) => el.textContent?.includes("Real House"));
    expect(demoItem?.querySelector(".icon")?.textContent).toBe("🧪");
    expect(existingItem?.querySelector(".icon")?.textContent).toBe("🏠");

    unmount(comp);
    target.remove();
  });
});
