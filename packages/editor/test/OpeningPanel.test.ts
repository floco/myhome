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

  it("scopes the sensor fetch to device_class=window for a window opening", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    setup({ opening: makeWindow() });
    await new Promise((r) => setTimeout(r, 0));
    const url = new URL((fetchMock.mock.calls[0][0] as string), "http://x");
    expect(url.searchParams.get("device_classes")).toBe("window");
  });

  it("scopes the sensor fetch to device_class=door,garage_door for a door opening", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    setup({ opening: makeDoor() });
    await new Promise((r) => setTimeout(r, 0));
    const url = new URL((fetchMock.mock.calls[0][0] as string), "http://x");
    expect(url.searchParams.get("device_classes")).toBe("door,garage_door");
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

describe("OpeningPanel — door kind and orientation", () => {
  it("shows a door kind select for a door, defaulting to hinged", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor() });
    const select = target.querySelector("select.door-kind") as HTMLSelectElement;
    expect(select).not.toBeNull();
    expect(select.value).toBe("hinged");
  });

  it("does not show a door kind select for a window", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow() });
    expect(target.querySelector("select.door-kind")).toBeNull();
  });

  it("shows hinge-side and swing-direction toggles for a hinged door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ swing: "right-out" }) });
    const hinge = target.querySelector("select.hinge-side") as HTMLSelectElement;
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    expect(hinge.value).toBe("right");
    expect(direction.value).toBe("out");
  });

  it("shows only the hinge-side toggle for a swinging door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "swinging" }) });
    expect(target.querySelector("select.hinge-side")).not.toBeNull();
    expect(target.querySelector("select.swing-direction")).toBeNull();
  });

  it("shows no orientation toggle for sliding or garage doors", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "sliding" }) });
    expect(target.querySelector("select.hinge-side")).toBeNull();
    expect(target.querySelector("select.swing-direction")).toBeNull();
  });

  it("updates swing when the hinge-side toggle changes, preserving direction", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeDoor({ swing: "left-out" }), onupdate });
    const hinge = target.querySelector("select.hinge-side") as HTMLSelectElement;
    hinge.value = "right";
    hinge.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ swing: "right-out" });
  });

  it("updates doorKind when the door kind select changes", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeDoor(), onupdate });
    const select = target.querySelector("select.door-kind") as HTMLSelectElement;
    select.value = "garage";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ doorKind: "garage" });
  });

  it("includes double in the door kind select", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor() });
    const select = target.querySelector("select.door-kind") as HTMLSelectElement;
    const values = [...select.options].map((o) => o.value);
    expect(values).toContain("double");
  });

  it("shows the swing-direction toggle but not hinge-side for a double door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "double", swing: "out" }) });
    expect(target.querySelector("select.hinge-side")).toBeNull();
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    expect(direction).not.toBeNull();
    expect(direction.value).toBe("out");
  });

  it("defaults the double door swing-direction toggle to in when swing is unset", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "double" }) });
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    expect(direction.value).toBe("in");
  });

  it("writes swing directly as in/out (no side) when the direction toggle changes on a double door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeDoor({ doorKind: "double", swing: "in" }), onupdate });
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    direction.value = "out";
    direction.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ swing: "out" });
  });

  it("shows a window-side toggle for a window, defaulting to in", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow() });
    const select = target.querySelector("select.window-side") as HTMLSelectElement;
    expect(select).not.toBeNull();
    expect(select.value).toBe("in");
  });

  it("updates windowSide when the window-side toggle changes", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeWindow(), onupdate });
    const select = target.querySelector("select.window-side") as HTMLSelectElement;
    select.value = "out";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ windowSide: "out" });
  });
});
