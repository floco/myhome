import { describe, it, expect, afterEach, beforeEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import App from "../src/App.svelte";

describe("App", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("renders the title and toolbar with the select tool active", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    expect(target.querySelector(".topbar h1")?.textContent).toBe("Floor Plan Editor");

    const buttons = Array.from(target.querySelectorAll(".toolbar button"));
    const labels = buttons.map((b) => b.textContent?.trim());
    expect(labels).toEqual(["Select", "Wall", "Divider", "Delete"]);

    const selectBtn = buttons.find((b) => b.textContent?.trim() === "Select")!;
    expect(selectBtn.className).toContain("active");

    const deleteBtn = buttons.find((b) => b.textContent?.trim() === "Delete")! as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(true);
  });

  it("selects a wall and deletes it with the Delete key", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    const wall = target.querySelector("polygon.wall")!;
    wall.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const deleteBtn = target.querySelectorAll(".toolbar button")[3] as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(false);

    const wallsBefore = target.querySelectorAll("polygon.wall").length;

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));
    flushSync();

    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore - 1);
    expect(deleteBtn.disabled).toBe(true);
  });
});
