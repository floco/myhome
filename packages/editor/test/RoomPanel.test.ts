import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import RoomPanel from "../src/lib/components/RoomPanel.svelte";
import type { Room } from "@myhome/geometry";

function makeRoom(overrides: Partial<Room> = {}): Room {
  return { id: "r1", label: "", haAreaId: null, polygon: null, areaM2: 12.5, ...overrides };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = { room: makeRoom(), haAreas: [{ area_id: "a1", name: "Living Room" }], onupdate: vi.fn(), ...overrides };
  const comp = mount(RoomPanel, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("RoomPanel — HA Area auto-fill", () => {
  it("fills the room label from the area name when the label is empty", () => {
    const onupdate = vi.fn();
    const { target } = setup({ room: makeRoom({ label: "" }), onupdate });
    const select = target.querySelector("select") as HTMLSelectElement;
    select.value = "a1";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith(expect.objectContaining({ haAreaId: "a1", label: "Living Room" }));
  });

  it("does not touch an existing custom label when the area changes", () => {
    const onupdate = vi.fn();
    const { target } = setup({ room: makeRoom({ label: "My Office" }), onupdate });
    const select = target.querySelector("select") as HTMLSelectElement;
    select.value = "a1";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ haAreaId: "a1" });
  });
});
