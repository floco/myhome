import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import App from "../src/App.svelte";

describe("App", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("renders the editor title", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    expect(target.querySelector("h1")?.textContent).toBe("Floor Plan Editor");
  });
});
