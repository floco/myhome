import { describe, it, expect, vi } from "vitest";
import { mount, unmount } from "svelte";
import NavMenu from "../src/lib/components/NavMenu.svelte";

describe("NavMenu", () => {
  it("lists Home before Floor Plan, pointing at # and #/plan", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NavMenu, {
      target,
      props: { currentRoute: "#/", expanded: true, onclose: vi.fn() },
    });

    const links = Array.from(target.querySelectorAll(".nav-item")).map((a) => ({
      href: (a as HTMLAnchorElement).getAttribute("href"),
      label: a.querySelector(".nav-label")?.textContent,
    }));

    expect(links[0]).toEqual({ href: "#/", label: "Home" });
    expect(links[1]).toEqual({ href: "#/plan", label: "Floor Plan" });

    unmount(comp);
    target.remove();
  });

  it("marks Home active at the default route and Floor Plan active at #/plan", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NavMenu, {
      target,
      props: { currentRoute: "#/plan", expanded: true, onclose: vi.fn() },
    });

    const items = Array.from(target.querySelectorAll(".nav-item"));
    const home = items.find((a) => a.querySelector(".nav-label")?.textContent === "Home")!;
    const plan = items.find((a) => a.querySelector(".nav-label")?.textContent === "Floor Plan")!;
    expect(home.classList.contains("active")).toBe(false);
    expect(plan.classList.contains("active")).toBe(true);

    unmount(comp);
    target.remove();
  });

  it("does not render a HomesSwitcher inside the nav", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NavMenu, {
      target,
      props: { currentRoute: "#/", expanded: true, onclose: vi.fn() },
    });

    expect(target.querySelector(".switcher")).toBeNull();
    expect(target.querySelector(".topbar-current")).toBeNull();

    unmount(comp);
    target.remove();
  });
});
