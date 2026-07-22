import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import { locale } from "svelte-i18n";
import ChoreRow from "../src/lib/components/ChoreRow.svelte";

describe("French locale smoke test", () => {
  afterEach(() => {
    locale.set("en");
  });

  it("renders French text when the locale is set to fr", () => {
    locale.set("fr");

    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ChoreRow, {
      target,
      props: { emoji: "🧹", name: "Sweep", dueLabel: "Aujourd'hui", dueColor: "#4caf50", oncomplete: () => {} },
    });
    flushSync();

    (target.querySelector(".done-btn") as HTMLButtonElement).click();
    flushSync();

    const input = target.querySelector(".note-input") as HTMLInputElement;
    expect(input.placeholder).toBe("Remarque (facultatif)");

    unmount(comp);
    target.remove();
  });
});
