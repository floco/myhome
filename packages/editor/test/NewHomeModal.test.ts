import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import NewHomeModal from "../src/lib/components/NewHomeModal.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

afterEach(() => {
  vi.restoreAllMocks();
  homesStore._reset();
});

function mountModal() {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(NewHomeModal, {
    target,
    props: { open: true, onclose: vi.fn() },
  });
  return { target, comp };
}

describe("NewHomeModal — demo option", () => {
  it("renders a demo radio option", async () => {
    const { target, comp } = mountModal();
    await tick();
    flushSync();
    const radios = target.querySelectorAll('input[type="radio"]');
    const values = Array.from(radios).map((r) => (r as HTMLInputElement).value);
    expect(values).toContain("demo");
    unmount(comp);
    target.remove();
  });

  it("submits with type 'demo' when the demo option is selected", async () => {
    const createHomeSpy = vi.spyOn(homesStore, "createHome").mockResolvedValue({
      id: "h1", name: "Demo House", type: "demo", enabledModules: [], createdAt: "",
    });
    const { target, comp } = mountModal();
    await tick();
    flushSync();

    const nameInput = target.querySelector('input[type="text"]') as HTMLInputElement;
    nameInput.value = "Demo House";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));

    const demoRadio = target.querySelector('input[type="radio"][value="demo"]') as HTMLInputElement;
    demoRadio.click();
    await tick();
    flushSync();

    const submitBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Create home"))!;
    submitBtn.click();
    await tick();
    flushSync();

    expect(createHomeSpy).toHaveBeenCalledWith("Demo House", "demo");
    unmount(comp);
    target.remove();
  });
});
