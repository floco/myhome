export interface Notification {
  type: "chore" | "low_stock" | "warranty";
  refId: string;
  title: string;
  detail: string;
  severity: "info" | "warning" | "critical";
}

export function createNotificationStore(getHomeId: () => string | null = () => null) {
  const notifications = $state<Notification[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/notifications`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const list: Notification[] = await resp.json();
      notifications.length = 0;
      for (const n of list) notifications.push(n);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  init();

  return {
    get notifications() { return notifications as Notification[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    refresh: init,
    reload: init,
  };
}
