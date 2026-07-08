import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsNav from "../src/lib/components/settings/SettingsNav.svelte";

const GROUPS = [
  { id: "general", icon: "⚙️", label: "General" },
  { id: "categories", icon: "🏷️", label: "Categories" },
  { id: "security", icon: "🔐", label: "Security & Access" },
];

describe("SettingsNav", () => {
  it("renders a nav button for each group", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange: vi.fn() } });
    flushSync();
    expect(target.querySelectorAll(".nav-item").length).toBe(3);
    expect(target.textContent).toContain("Categories");
    unmount(app);
  });

  it("marks the active group's button with the active class", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "categories", onchange: vi.fn() } });
    flushSync();
    const active = target.querySelector(".nav-item.active");
    expect(active?.textContent).toContain("Categories");
    unmount(app);
  });

  it("calls onchange with the clicked group's id", () => {
    const target = document.createElement("div");
    const onchange = vi.fn();
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange } });
    flushSync();
    const buttons = [...target.querySelectorAll<HTMLButtonElement>(".nav-item")];
    const securityBtn = buttons.find((b) => b.textContent?.includes("Security & Access"))!;
    securityBtn.click();
    expect(onchange).toHaveBeenCalledWith("security");
    unmount(app);
  });

  it("renders a select dropdown with matching options for mobile", () => {
    const target = document.createElement("div");
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange: vi.fn() } });
    flushSync();
    const select = target.querySelector(".nav-select") as HTMLSelectElement;
    expect(select).not.toBeNull();
    const values = [...select.querySelectorAll("option")].map((o) => o.value);
    expect(values).toEqual(["general", "categories", "security"]);
    unmount(app);
  });

  it("calls onchange when the dropdown value changes", () => {
    const target = document.createElement("div");
    const onchange = vi.fn();
    const app = mount(SettingsNav, { target, props: { groups: GROUPS, active: "general", onchange } });
    flushSync();
    const select = target.querySelector(".nav-select") as HTMLSelectElement;
    select.value = "categories";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onchange).toHaveBeenCalledWith("categories");
    unmount(app);
  });
});
