<script lang="ts">
  import type { CostCategory } from "../settingsStore.svelte";
  import { _ } from "svelte-i18n";

  interface Props {
    category: CostCategory;
    screenX: number;
    screenY: number;
    onopen: () => void;
    onremove: () => void;
    onclose: () => void;
  }

  let { category, screenX, screenY, onopen, onremove, onclose }: Props = $props();
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="popup" style="left:{screenX}px;top:{screenY + 30}px" onclick={(e) => e.stopPropagation()}>
  <div class="popup-name">{category.emoji} {category.name}</div>
  {#if category.unit}
    <div class="popup-row">{$_('costs.pinPopup.unit', { values: { unit: category.unit } })}</div>
  {/if}
  <div class="popup-actions">
    <button onclick={onopen}>{$_('costs.open')}</button>
    <button onclick={onremove}>{$_('costs.remove')}</button>
    <button onclick={onclose}>{$_('common.close')}</button>
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
