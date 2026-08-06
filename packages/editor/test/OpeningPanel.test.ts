import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import OpeningPanel from "../src/lib/components/OpeningPanel.svelte";
import type { Opening } from "@myhome/geometry";

function makeWindow(overrides: Partial<Opening> = {}): Opening {
  return { id: "o1", wallId: "w1", type: "window", offset: 0, width: 1, ...overrides };
}

function makeDoor(overrides: Partial<Opening> = {}): Opening {
  return { id: "o2", wallId: "w1", type: "door", offset: 0, width: 0.9, ...overrides };
}

let target: HTMLElement;
let app: ReturnType<typeof mount> | undefined;

function setup(overrides: Record<string, unknown> = {}) {
  target = document.createElement("div");
  document.body.appendChild(target);
  const props = { opening: makeWindow(), areaIds: ["living_room"], onupdate: vi.fn(), ...overrides };
  app = mount(OpeningPanel, { target, props });
  flushSync();
  return { props };
}

afterEach(() => {
  if (app) { unmount(app); app = undefined; }
  target?.remove();
});

describe("OpeningPanel — sensor picker", () => {
  it("fetches binary_sensor entities scoped to the given area(s)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ entity_id: "binary_sensor.front_window", name: "Front Window" }],
    }));
    setup();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const options = Array.from(target.querySelectorAll("select")[0].querySelectorAll("option"));
    expect(options.some((o) => o.textContent === "Front Window")).toBe(true);
    expect((fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]).toContain("domain=binary_sensor");
  });

  it("shows a hint and disables pickers when there is no linked area", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ areaIds: [] });
    expect(target.querySelector(".hint")).not.toBeNull();
    expect((target.querySelectorAll("select")[0] as HTMLSelectElement).disabled).toBe(true);
  });

  it("calls onupdate with the selected entity id", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ onupdate });
    const select = target.querySelectorAll("select")[0] as HTMLSelectElement;
    select.value = "";
    const opt = document.createElement("option");
    opt.value = "binary_sensor.front_window";
    select.appendChild(opt);
    select.value = "binary_sensor.front_window";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ haEntityId: "binary_sensor.front_window" });
  });
});

describe("OpeningPanel — shutter fields", () => {
  it("shows shutter fields for a window", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow() });
    expect(target.querySelector('input[type="checkbox"]')).not.toBeNull();
  });

  it("does not show shutter fields for a door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor() });
    expect(target.querySelector('input[type="checkbox"]')).toBeNull();
  });

  it("clears shutterEntityId when hasShutter is unchecked", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      onupdate,
    });
    const checkbox = target.querySelector('input[type="checkbox"]') as HTMLInputElement;
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ hasShutter: false, shutterEntityId: null });
  });

  it("shows open/close/stop controls once a shutter entity is linked", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }) });
    expect(target.querySelector(".shutter-controls")).not.toBeNull();
    expect(target.querySelectorAll(".shutter-controls button")).toHaveLength(3);
  });

  it("posts the cover action when a control button is clicked", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.startsWith("/api/ha/entities")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => ({ ok: true }) });
    });
    vi.stubGlobal("fetch", fetchMock);
    setup({ opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }) });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    fetchMock.mockClear();
    const openBtn = target.querySelectorAll(".shutter-controls button")[0] as HTMLButtonElement;
    openBtn.click();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ha/cover/cover.front_window_shutter/open",
      { method: "POST" },
    );
  });
});
