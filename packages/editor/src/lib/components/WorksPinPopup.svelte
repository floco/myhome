<script lang="ts">
  import type { Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    work: Work;
    settingsStore: SettingsStore;
    screenX: number;
    screenY: number;
    onopen: () => void;
    onremove: () => void;
    onclose: () => void;
  }
  let { work, settingsStore, screenX, screenY, onopen, onremove, onclose }: Props = $props();

  const category = $derived(
    work.categoryId ? settingsStore.workCategories.find(c => c.id === work.categoryId) : null
  );
  const supplier = $derived(
    work.supplierId ? settingsStore.suppliers.find(s => s.id === work.supplierId) : null
  );

  function statusLabel(status: Work["status"]): string {
    if (status === "in_progress") return "In progress";
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  function statusColor(status: Work["status"]): string {
    if (status === "done") return "#33aa66";
    if (status === "in_progress") return "#3388cc";
    return "#cc8833";
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="popup" style="left:{screenX}px;top:{screenY + 30}px" onclick={(e) => e.stopPropagation()}>
  <div class="popup-name">{category?.emoji ?? "🔧"} {work.title}</div>
  <div class="popup-row">
    <span class="status-chip" style="background:{statusColor(work.status)}22;color:{statusColor(work.status)};border:1px solid {statusColor(work.status)}44">
      {statusLabel(work.status)}
    </span>
  </div>
  {#if supplier}
    <div class="popup-row">{supplier.name}</div>
  {/if}
  <div class="popup-actions">
    <button onclick={onopen}>📂 Open</button>
    <button onclick={onremove}>✕ Remove</button>
    <button onclick={onclose}>Close</button>
  </div>
</div>

<style>
  .popup {
    position: absolute;
    background: #1e1e3a; border: 1px solid #3a3a5a; border-radius: 8px;
    padding: 10px 14px; min-width: 180px; z-index: 60;
    box-shadow: 0 4px 16px #0006; font-family: sans-serif;
    transform: translateX(-50%);
  }
  .popup-name { font-size: 13px; color: #eee; font-weight: 600; margin-bottom: 6px; }
  .popup-row { font-size: 11px; color: #99a; margin-bottom: 4px; }
  .status-chip { padding: 1px 6px; border-radius: 3px; font-size: 10px; }
  .popup-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
  .popup-actions button {
    border: 1px solid #3a3a5a; background: #111128; color: #aaa;
    padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer;
  }
  .popup-actions button:hover { background: #2a2a5a; color: #eee; }
</style>
