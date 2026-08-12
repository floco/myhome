<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Chore, Assignment } from "../choreStore.svelte";
  import { formatDate } from "../dateFormat";

  interface Props {
    chore: Chore;
    assignment: Assignment;
    screenX: number;
    screenY: number;
    oncomplete: () => void;
    oncompleteall: () => void;
    onremove: () => void;
    onclose: () => void;
    onlabelchange: (label: string) => void;
    ondetails: () => void;
  }

  let { chore, assignment, screenX, screenY, oncomplete, oncompleteall, onremove, onclose, onlabelchange, ondetails }: Props = $props();

  const overdue = $derived(new Date(assignment.nextDueDate).getTime() < Date.now());

  // Clamp into the viewport -- on narrow mobile screens a badge near the
  // canvas edge would otherwise position most of the popup off-screen.
  const clampedLeft = $derived(Math.max(4, Math.min(screenX + 26, window.innerWidth - 212)));
  const clampedTop = $derived(Math.max(4, Math.min(screenY - 20, window.innerHeight - 192)));

  function handleLabelBlur(e: FocusEvent): void {
    const value = (e.target as HTMLInputElement).value.trim();
    if (value === (assignment.label ?? "")) return;
    onlabelchange(value);
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{clampedLeft}px;top:{clampedTop}px"
  onclick={(e) => e.stopPropagation()}
>
  <div class="popup-name">{chore.name}</div>
  <input
    class="popup-label-input"
    placeholder={$_('chores.editModal.labelPlaceholder')}
    value={assignment.label ?? ""}
    onblur={handleLabelBlur}
  />
  <div class="popup-due" class:overdue>
    {overdue ? $_('chores.badgePopup.overdueSince') : $_('chores.badgePopup.due')}: {formatDate(assignment.nextDueDate)}
  </div>
  <div class="popup-actions">
    <button class="details-btn" onclick={ondetails} title={$_('chores.badgePopup.details')}>🔍 {$_('chores.badgePopup.details')}</button>
    <button onclick={oncompleteall}>✓ {$_('chores.badgePopup.allDone')}</button>
    <button onclick={oncomplete}>✓ {$_('chores.badgePopup.thisRoom')}</button>
    <button onclick={onremove}>✕ {$_('chores.badgePopup.remove')}</button>
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
  .popup-label-input {
    width: 100%;
    box-sizing: border-box;
    padding: 3px 6px;
    margin-bottom: 8px;
    border: 1px solid #444;
    border-radius: 3px;
    background: #1e1e2e;
    color: #ccc;
    font-size: 11px;
  }
  .popup-label-input:focus { outline: none; border-color: #6a6aaa; }
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
