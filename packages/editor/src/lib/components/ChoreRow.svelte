<script lang="ts">
  import { _ } from "svelte-i18n";
  import ChoreCompleteModal from "./ChoreCompleteModal.svelte";

  interface Props {
    emoji: string;
    name: string;
    location?: string;
    dueLabel: string;
    dueColor: string;
    oncomplete: (notes: string, completedOn?: string) => void;
  }
  let { emoji, name, location, dueLabel, dueColor, oncomplete }: Props = $props();

  let completing = $state(false);

  function start(e: Event): void {
    e.stopPropagation();
    completing = true;
  }

  function confirm(notes: string, completedOn?: string): void {
    completing = false;
    if (completedOn) oncomplete(notes, completedOn);
    else oncomplete(notes);
  }
</script>

<div class="chore-row">
  <span class="emoji">{emoji}</span>
  <span class="name">{name}</span>
  {#if location}<span class="location">{location}</span>{/if}
  <span class="due" style="color:{dueColor}">{dueLabel}</span>
  <button class="done-btn" onclick={start} title={$_('chores.row.markDone')}>✓</button>
</div>

{#if completing}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div onclick={(e) => e.stopPropagation()}>
    <ChoreCompleteModal title={`${emoji} ${name}`} onclose={() => { completing = false; }} onconfirm={confirm} />
  </div>
{/if}

<style>
  .chore-row {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 16px; border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .chore-row:hover { background: var(--surface-hover); }

  .emoji { font-size: 16px; flex-shrink: 0; width: 22px; text-align: center; }
  .name { flex: 2; min-width: 80px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .location { flex: 2; min-width: 80px; color: var(--text-muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .due { flex: 1; min-width: 70px; font-size: 12px; text-align: right; white-space: nowrap; }

  .done-btn {
    padding: 4px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--success); color: var(--accent-contrast); cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0; touch-action: manipulation;
  }
  .done-btn:hover { opacity: 0.85; }
  .done-btn:disabled { opacity: 0.5; cursor: default; }

  @media (max-width: 500px) {
    .chore-row { flex-wrap: wrap; gap: 6px; }
    .location { flex-basis: 100%; order: 3; }
    .due { text-align: left; }
  }
</style>
