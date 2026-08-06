import { wsUrl } from "./apiUrl";

export interface HaEntityState {
  state: string;
  attributes: Record<string, unknown>;
}

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 15000];

export function createHaStateStore() {
  let states = $state(new Map<string, HaEntityState>());
  let active = false;
  let entityIds = new Set<string>();
  let socket: WebSocket | null = null;
  let reconnectAttempt = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function clearReconnectTimer(): void {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function connect(): void {
    if (!active || entityIds.size === 0 || socket) return;
    const ws = new WebSocket(wsUrl("/api/ha/ws"));
    socket = ws;
    ws.onopen = () => {
      reconnectAttempt = 0;
      ws.send(JSON.stringify({ entity_ids: [...entityIds] }));
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data as string) as {
        entity_id: string; state: string; attributes: Record<string, unknown>;
      };
      const next = new Map(states);
      next.set(data.entity_id, { state: data.state, attributes: data.attributes });
      states = next;
    };
    ws.onclose = () => {
      socket = null;
      scheduleReconnect();
    };
    ws.onerror = () => {
      ws.close();
    };
  }

  function scheduleReconnect(): void {
    clearReconnectTimer();
    if (!active || entityIds.size === 0) return;
    const delay = RECONNECT_DELAYS_MS[Math.min(reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)];
    reconnectAttempt += 1;
    reconnectTimer = setTimeout(connect, delay);
  }

  function disconnect(): void {
    clearReconnectTimer();
    reconnectAttempt = 0;
    if (socket) {
      const ws = socket;
      socket = null;
      ws.onclose = null;
      ws.close();
    }
  }

  function setActive(next: boolean): void {
    if (active === next) return;
    active = next;
    if (active) connect();
    else disconnect();
  }

  function setEntityIds(ids: Iterable<string>): void {
    entityIds = new Set(ids);
    if (entityIds.size === 0) {
      disconnect();
      return;
    }
    if (!active) return;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ entity_ids: [...entityIds] }));
    } else if (!socket) {
      connect();
    }
  }

  return {
    get states() { return states; },
    setActive,
    setEntityIds,
    disconnect,
  };
}
