<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createConsumableStore, Consumable } from "../consumableStore.svelte";
  import { stockStatus } from "../consumableStore.svelte";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;

  interface Props {
    consumable: Consumable;
    store: ConsumableStore;
    screenX: number;
    screenY: number;
    onedit: () => void;
    onremove: () => void;
    onclose: () => void;
  }

  let { consumable, store, screenX, screenY, onedit, onremove, onclose }: Props = $props();

  const STATE_COLOR: Record<string, string> = {
    ok: "#4caf50",
    low: "#ff9800",
    empty: "#f44336",
  };

  function stateLabel(state: string): string {
    if (state === "ok") return $_('consumables.pinPopup.inStock');
    if (state === "low") return $_('consumables.pinPopup.lowStock');
    return $_('consumables.pinPopup.empty');
  }

  let newQty = $state(String(consumable.quantity));
  let note = $state("");
  let updating = $state(false);
  let updateError = $state<string | null>(null);

  const st = $derived(stockStatus(consumable));
  const color = $derived(STATE_COLOR[st]);

  async function handleUpdate(): Promise<void> {
    const qty = parseFloat(newQty);
    if (isNaN(qty)) {
      updateError = $_('consumables.pinPopup.invalidQuantity');
      return;
    }
    updating = true;
    updateError = null;
    try {
      await store.updateStock(consumable.id, qty, note);
      onclose();
    } catch {
      updateError = $_('consumables.pinPopup.updateFailed');
    } finally {
      updating = false;
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{screenX}px;top:{screenY + 30}px"
  onclick={(e) => e.stopPropagation()}
>
  <div class="popup-name">{consumable.emoji} {consumable.name}</div>
  <div class="popup-status" style="color:{color}">
    {stateLabel(st)} — {consumable.quantity} {consumable.unit}
  </div>

  <div class="quick-update">
    <input class="qty-input" type="number" bind:value={newQty} min="0" step="any" />
    <span class="unit-label">{consumable.unit}</span>
    <input class="note-input" type="text" bind:value={note} placeholder={$_('consumables.pinPopup.notePlaceholder')} />
    <button class="update-btn" onclick={handleUpdate} disabled={updating}>
      {updating ? "…" : "✓"}
    </button>
  </div>
  {#if updateError}<div class="popup-error">{updateError}</div>{/if}

  <div class="popup-actions">
    <button onclick={onedit}>✏️ {$_('common.edit')}</button>
    <button onclick={onremove}>✕ {$_('consumables.pinPopup.removePin')}</button>
    <button onclick={onclose}>{$_('common.close')}</button>
  </div>
</div>

<style>
  .popup {
    position: absolute;
    background: #1e1e3a;
    border: 1px solid #3a3a5a;
    border-radius: 8px;
    padding: 10px 14px;
    min-width: 220px;
    z-index: 60;
    box-shadow: 0 4px 16px #0006;
    font-family: sans-serif;
    transform: translateX(-50%);
  }
  .popup-name { font-size: 13px; color: #eee; font-weight: 600; margin-bottom: 4px; }
  .popup-status { font-size: 11px; margin-bottom: 8px; }
  .quick-update { display: flex; align-items: center; gap: 4px; margin-bottom: 4px; }
  .qty-input {
    width: 52px; padding: 3px 6px; background: #111128; border: 1px solid #3a3a5a;
    border-radius: 4px; color: #eee; font-size: 12px;
  }
  .unit-label { font-size: 11px; color: #667; flex-shrink: 0; }
  .note-input {
    flex: 1; padding: 3px 6px; background: #111128; border: 1px solid #3a3a5a;
    border-radius: 4px; color: #eee; font-size: 12px;
  }
  .update-btn {
    border: none; background: #27ae60; color: #fff; padding: 3px 8px;
    border-radius: 4px; font-size: 12px; cursor: pointer;
  }
  .update-btn:disabled { opacity: 0.5; cursor: default; }
  .popup-error { font-size: 11px; color: #f44336; margin-bottom: 4px; }
  .popup-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
  .popup-actions button {
    border: 1px solid #3a3a5a; background: #111128; color: #aaa;
    padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer;
  }
  .popup-actions button:hover { background: #2a2a5a; color: #eee; }
</style>
