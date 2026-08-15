<script lang="ts">
  import { _ } from "svelte-i18n";

  interface Props {
    scheduleFromDue: boolean;
    idPrefix: string;
  }

  let { scheduleFromDue = $bindable(), idPrefix }: Props = $props();
</script>

<div class="anchor-group" role="radiogroup" aria-label={$_('chores.editModal.anchorGroupLabel')}>
  <label class="anchor-option" for="{idPrefix}-due">
    <input
      type="radio"
      id="{idPrefix}-due"
      name="{idPrefix}-anchor"
      checked={scheduleFromDue}
      onchange={() => { scheduleFromDue = true; }}
    />
    <span class="anchor-text">
      <span class="anchor-title">{$_('chores.editModal.anchorDueTitle')}</span>
      <span class="anchor-desc">{$_('chores.editModal.anchorDueDesc')}</span>
    </span>
  </label>
  <label class="anchor-option" for="{idPrefix}-completion">
    <input
      type="radio"
      id="{idPrefix}-completion"
      name="{idPrefix}-anchor"
      checked={!scheduleFromDue}
      onchange={() => { scheduleFromDue = false; }}
    />
    <span class="anchor-text">
      <span class="anchor-title">{$_('chores.editModal.anchorCompletionTitle')}</span>
      <span class="anchor-desc">{$_('chores.editModal.anchorCompletionDesc')}</span>
    </span>
  </label>
</div>

<style>
  .anchor-group { display: flex; flex-direction: column; gap: 6px; }
  .anchor-option {
    display: flex; align-items: flex-start; gap: 8px; cursor: pointer;
    padding: 8px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt);
  }
  .anchor-option:has(input:checked) { border-color: var(--accent); background: var(--surface-hover); }
  .anchor-option input[type="radio"] { margin-top: 2px; flex-shrink: 0; }
  .anchor-text { display: flex; flex-direction: column; gap: 2px; }
  .anchor-title { font-size: 12px; font-weight: 500; color: var(--text); }
  .anchor-desc { font-size: 11px; color: var(--text-faint); line-height: 1.35; }
</style>
