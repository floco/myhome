<script lang="ts">
  import type { Chore, Assignment } from "../choreStore.svelte";

  interface Props {
    chore: Chore;
    assignment: Assignment;
    screenX: number;
    screenY: number;
    oncomplete: () => void;
    onremove: () => void;
    onclose: () => void;
  }

  let { chore, assignment, screenX, screenY, oncomplete, onremove, onclose }: Props = $props();

  function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  const overdue = $derived(new Date(chore.nextDueDate).getTime() < Date.now());
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{screenX + 26}px;top:{screenY - 20}px"
  onclick={(e) => e.stopPropagation()}
>
  <div class="popup-name">{chore.name}</div>
  <div class="popup-due" class:overdue>
    {overdue ? "Overdue since" : "Due"}: {formatDate(chore.nextDueDate)}
  </div>
  <div class="popup-actions">
    <button onclick={oncomplete}>✓ Mark done</button>
    <button onclick={onremove}>✕ Remove</button>
    <button class="close-btn" onclick={onclose}>✕</button>
  </div>
</div>

<style>
  .popup {
    position: fixed;
    background: #2a2a3e;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 10px;
    min-width: 180px;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    font-size: 12px;
    color: #ccc;
  }
  .popup-name {
    font-weight: 600;
    margin-bottom: 4px;
    color: #eee;
  }
  .popup-due {
    color: #888;
    margin-bottom: 8px;
  }
  .popup-due.overdue {
    color: #f44336;
  }
  .popup-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .popup-actions button {
    padding: 3px 8px;
    border: none;
    border-radius: 3px;
    background: #3a3a5a;
    color: #ccc;
    cursor: pointer;
    font-size: 11px;
  }
  .popup-actions button:hover {
    background: #4a4a6a;
  }
  .close-btn {
    margin-left: auto;
  }
</style>
