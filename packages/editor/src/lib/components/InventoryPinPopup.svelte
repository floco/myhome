<script lang="ts">
  import type { InventoryItem } from "../inventoryStore.svelte";

  interface Props {
    item: InventoryItem;
    screenX: number;
    screenY: number;
    onedit: () => void;
    onremove: () => void;
    onclose: () => void;
  }
  let { item, screenX, screenY, onedit, onremove, onclose }: Props = $props();

  function warrantyLabel(): string {
    if (!item.warrantyExpiryDate) return "—";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    const days = Math.round((expiry - now) / 86400000);
    if (days < 0) return "Expired";
    if (days === 0) return "Expires today";
    return `${days}d remaining`;
  }

  function warrantyColor(): string {
    if (!item.warrantyExpiryDate) return "#556";
    const expiry = new Date(item.warrantyExpiryDate).getTime();
    const now = Date.now();
    if (expiry < now) return "#f44336";
    if (expiry - now <= 30 * 86400 * 1000) return "#ff9800";
    return "#4caf50";
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{screenX}px;top:{screenY + 30}px"
  onclick={(e) => e.stopPropagation()}
>
  <div class="popup-name">{item.emoji} {item.name}</div>
  {#if item.category}
    <div class="popup-row">{item.category}</div>
  {/if}
  <div class="popup-row" style="color:{warrantyColor()}">
    Warranty: {warrantyLabel()}
  </div>
  <div class="popup-actions">
    <button onclick={onedit}>✏️ Edit</button>
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
  .popup-row { font-size: 11px; color: #99a; margin-bottom: 3px; }
  .popup-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
  .popup-actions button {
    border: 1px solid #3a3a5a; background: #111128; color: #aaa;
    padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer;
  }
  .popup-actions button:hover { background: #2a2a5a; color: #eee; }
</style>
