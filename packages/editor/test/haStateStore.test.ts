import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createHaStateStore } from "../src/lib/haStateStore.svelte";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 3;

  url: string;
  readyState = FakeWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }
  send(data: string): void { this.sent.push(data); }
  close(): void {
    this.closed = true;
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }
  open(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }
  receive(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("createHaStateStore", () => {
  it("does not connect until both active and entityIds are set", () => {
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    expect(FakeWebSocket.instances).toHaveLength(0);
    store.setActive(true);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("sends entity_ids on open and merges incoming state updates", () => {
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    expect(JSON.parse(ws.sent[0])).toEqual({ entity_ids: ["binary_sensor.front_door"] });

    ws.receive({ entity_id: "binary_sensor.front_door", state: "on", attributes: { device_class: "door" } });
    expect(store.states.get("binary_sensor.front_door")).toEqual({ state: "on", attributes: { device_class: "door" } });
  });

  it("closes the socket when entityIds becomes empty", () => {
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    store.setEntityIds([]);
    expect(ws.closed).toBe(true);
  });

  it("closes the socket when set inactive, and does not reconnect", () => {
    vi.useFakeTimers();
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    store.setActive(false);
    expect(ws.closed).toBe(true);
    vi.advanceTimersByTime(20000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("reconnects with backoff after the socket drops while still active", () => {
    vi.useFakeTimers();
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].close();
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("preserves last-known state across a reconnect", () => {
    vi.useFakeTimers();
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    ws.receive({ entity_id: "binary_sensor.front_door", state: "on", attributes: {} });
    ws.close();
    vi.advanceTimersByTime(1000);
    expect(store.states.get("binary_sensor.front_door")).toEqual({ state: "on", attributes: {} });
  });
});
