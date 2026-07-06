<!-- packages/editor/src/lib/components/NotificationBell.svelte -->
<script lang="ts">
  import type { createNotificationStore, Notification } from "../notificationStore.svelte";

  type NotificationStore = ReturnType<typeof createNotificationStore>;

  interface Props {
    store: NotificationStore;
    onnavigate: (n: Notification) => void;
  }
  let { store, onnavigate }: Props = $props();

  let dropdownOpen = $state(false);

  const GROUP_LABELS: Record<Notification["type"], string> = {
    chore: "Chores",
    low_stock: "Low Stock",
    warranty: "Warranty",
  };
  const GROUP_ORDER: Notification["type"][] = ["chore", "low_stock", "warranty"];

  const groups = $derived.by(() => {
    const byType = new Map<string, Notification[]>();
    for (const n of store.notifications) {
      if (!byType.has(n.type)) byType.set(n.type, []);
      byType.get(n.type)!.push(n);
    }
    return GROUP_ORDER
      .filter((t) => byType.has(t))
      .map((t) => ({ type: t, label: GROUP_LABELS[t], items: byType.get(t)! }));
  });

  function handleClick(): void {
    dropdownOpen = !dropdownOpen;
    if (dropdownOpen) store.refresh();
  }

  function handleClickOutside(e: MouseEvent): void {
    if (!(e.target as HTMLElement).closest(".notif-bell-wrap")) dropdownOpen = false;
  }

  function select(n: Notification): void {
    dropdownOpen = false;
    onnavigate(n);
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="notif-bell-wrap">
  <button class="icon-btn notif-bell" title="Notifications" onclick={handleClick}>
    🔔
    {#if store.notifications.length > 0}
      <span class="notif-badge">{store.notifications.length}</span>
    {/if}
  </button>

  {#if dropdownOpen}
    <div class="notif-dropdown">
      {#if store.notifications.length === 0}
        <div class="notif-empty">No notifications</div>
      {/if}
      {#each groups as group (group.type)}
        <div class="notif-group-label">{group.label}</div>
        {#each group.items as n (n.type + n.refId)}
          <button class="notif-item" onclick={() => select(n)}>
            <div class="notif-item-title">{n.title}</div>
            <div class="notif-item-detail">{n.detail}</div>
          </button>
        {/each}
      {/each}
    </div>
  {/if}
</div>

<style>
  .notif-bell-wrap { position: relative; }
  .notif-bell { position: relative; }
  .notif-badge {
    position: absolute; top: 2px; right: 2px;
    background: #f44336; color: white;
    font-size: 10px; line-height: 1; font-weight: 600;
    border-radius: 999px; padding: 2px 5px; min-width: 14px; text-align: center;
  }
  .notif-dropdown {
    position: absolute; top: calc(100% + 4px); right: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 200; padding: 4px; min-width: 260px; max-height: 360px; overflow-y: auto;
  }
  .notif-empty { padding: 16px; font-size: 12px; color: var(--text-faint); text-align: center; }
  .notif-group-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--text-faint); padding: 8px 10px 4px;
  }
  .notif-item {
    display: block; width: 100%; text-align: left;
    padding: 8px 10px; border: none; background: none; border-radius: var(--radius-md); cursor: pointer;
  }
  .notif-item:hover { background: var(--surface-hover); }
  .notif-item-title { font-size: 13px; color: var(--text); font-weight: 500; }
  .notif-item-detail { font-size: 11px; color: var(--text-faint); margin-top: 1px; }
</style>
