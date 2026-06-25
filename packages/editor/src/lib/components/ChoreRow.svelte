<script lang="ts">
  interface Props {
    emoji: string;
    name: string;
    location?: string;
    dueLabel: string;
    dueColor: string;
    oncomplete: (notes: string) => void;
  }
  let { emoji, name, location, dueLabel, dueColor, oncomplete }: Props = $props();

  let completing = $state(false);
  let notes = $state("");

  function start(e: Event): void {
    e.stopPropagation();
    completing = true;
    notes = "";
  }

  function confirm(e: Event): void {
    e.stopPropagation();
    completing = false;
    oncomplete(notes);
  }

  function cancel(e: Event): void {
    e.stopPropagation();
    completing = false;
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter") confirm(e);
    if (e.key === "Escape") cancel(e);
  }
</script>

<div class="chore-row">
  <span class="emoji">{emoji}</span>
  <span class="name">{name}</span>
  {#if location}<span class="location">{location}</span>{/if}
  <span class="due" style="color:{dueColor}">{dueLabel}</span>
  {#if completing}
    <input
      class="note-input"
      bind:value={notes}
      placeholder="Note (optional)"
      on:click={(e) => e.stopPropagation()}
      on:keydown={handleKeydown}
    />
    <button class="done-btn confirm" on:click={confirm}>✓</button>
    <button class="cancel-btn" on:click={cancel}>✕</button>
  {:else}
    <button class="done-btn" on:click={start} title="Mark done">✓</button>
  {/if}
</div>

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

  .note-input {
    flex: 1; min-width: 80px; max-width: 160px;
    padding: 3px 8px; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); font-size: 11px;
  }
  .note-input:focus { outline: none; border-color: var(--accent); }
  .done-btn {
    padding: 4px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--success); color: var(--accent-contrast); cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0; touch-action: manipulation;
  }
  .done-btn:hover { opacity: 0.85; }
  .done-btn:disabled { opacity: 0.5; cursor: default; }
  .cancel-btn {
    padding: 4px 8px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 12px;
    min-height: 30px; flex-shrink: 0;
  }
  .cancel-btn:hover { background: var(--surface-hover); }

  @media (max-width: 500px) {
    .chore-row { flex-wrap: wrap; gap: 6px; }
    .location { flex-basis: 100%; order: 3; }
    .due { text-align: left; }
  }
</style>
