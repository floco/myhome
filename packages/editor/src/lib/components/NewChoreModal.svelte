<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    open: boolean;
    store: ChoreStore;
    onclose: () => void;
  }

  let { open, store, onclose }: Props = $props();

  let name = $state("");
  let emoji = $state("📋");
  let freqN = $state(30);
  let freqUnit = $state<"days" | "weeks" | "months" | "years">("days");
  let nextDue = $state(new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));
  let scheduleFromDue = $state(false);
  let saving = $state(false);
  let error = $state("");

  const UNIT_DAYS: Record<string, number> = { days: 1, weeks: 7, months: 30, years: 365 };

  async function handleCreate(): Promise<void> {
    if (!name.trim()) return;
    saving = true;
    error = "";
    try {
      await store.createChore({
        name: name.trim(),
        emoji: emoji.trim() || "📋",
        periodDays: freqN * UNIT_DAYS[freqUnit],
        frequencyType: "interval",
        frequency: freqN,
        frequencyMetadata: { unit: freqUnit },
        scheduleFromDue,
        nextDueDate: new Date(nextDue).toISOString(),
        description: "",
        donetickId: null,
      });
      reset();
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to create";
    } finally {
      saving = false;
    }
  }

  function reset(): void {
    name = ""; emoji = "📋"; freqN = 30; freqUnit = "days";
    nextDue = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
    scheduleFromDue = false; error = "";
  }

  function handleBackdropKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") { reset(); onclose(); }
  }

  function handleFormKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleCreate(); }
    if (e.key === "Escape") { reset(); onclose(); }
  }
</script>

{#if open}
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onclose} onkeydown={handleBackdropKeydown} role="presentation">
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="modal" onclick={(e) => e.stopPropagation()} onkeydown={handleFormKeydown} role="presentation">
    <div class="modal-header">
      <h2>New Chore</h2>
      <button class="close-btn" onclick={() => { reset(); onclose(); }}>✕</button>
    </div>

    <div class="modal-body">
      <div class="field">
        <label for="chore-name">Name</label>
        <!-- svelte-ignore a11y_autofocus -->
        <input id="chore-name" bind:value={name} placeholder="Chore name" autofocus />
      </div>

      <div class="field">
        <label for="chore-emoji">Emoji</label>
        <input id="chore-emoji" bind:value={emoji} maxlength="4" class="emoji-input" />
      </div>

      <div class="field">
        <label>Repeat every</label>
        <div class="freq-row">
          <input type="number" bind:value={freqN} min="1" class="freq-n" />
          <select bind:value={freqUnit}>
            <option value="days">days</option>
            <option value="weeks">weeks</option>
            <option value="months">months</option>
            <option value="years">years</option>
          </select>
        </div>
      </div>

      <div class="field">
        <label for="chore-due">First due</label>
        <input id="chore-due" type="date" bind:value={nextDue} />
      </div>

      <div class="field-row">
        <input type="checkbox" id="sfd" bind:checked={scheduleFromDue} />
        <label for="sfd" class="checkbox-label" title="Next due = planned date + period (not completion date + period)">
          Schedule from due date
        </label>
      </div>

      {#if error}<div class="error">{error}</div>{/if}
    </div>

    <div class="modal-footer">
      <button onclick={() => { reset(); onclose(); }}>Cancel</button>
      <button class="primary-btn" disabled={!name.trim() || saving} onclick={handleCreate}>
        {saving ? "Creating…" : "Create"}
      </button>
    </div>
  </div>
</div>
{/if}

<style>
  .backdrop {
    position: fixed; inset: 0; z-index: 200;
    background: rgba(0, 0, 0, 0.65);
    display: flex; align-items: center; justify-content: center;
  }
  .modal {
    background: #252535; border: 1px solid #444; border-radius: 8px;
    width: 360px; max-width: calc(100vw - 32px);
    display: flex; flex-direction: column;
    font-family: sans-serif; color: #ccc;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }
  .modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; border-bottom: 1px solid #333;
  }
  .modal-header h2 { margin: 0; font-size: 15px; color: #eee; font-weight: 600; }
  .close-btn {
    border: none; background: transparent; color: #666; cursor: pointer;
    font-size: 16px; width: 28px; height: 28px; border-radius: 4px;
    display: flex; align-items: center; justify-content: center; padding: 0;
  }
  .close-btn:hover { background: #3a3a5a; color: #eee; }

  .modal-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field label { font-size: 11px; color: #888; }
  .field-row { display: flex; align-items: center; gap: 8px; }
  .checkbox-label { font-size: 12px; color: #aaa; cursor: pointer; }

  input, select {
    padding: 7px 10px; background: #1a1a2e; border: 1px solid #444; border-radius: 4px;
    color: #ccc; font-size: 13px; width: 100%; box-sizing: border-box;
  }
  input:focus, select:focus { outline: none; border-color: #668; }
  input[type="checkbox"] { width: auto; }
  input[type="date"] { width: 160px; }
  .emoji-input { width: 80px; }
  .freq-row { display: flex; gap: 8px; }
  .freq-n { width: 80px; }
  .freq-row select { flex: 1; }

  .error { font-size: 11px; color: #f66; padding: 4px 0; }

  .modal-footer {
    display: flex; justify-content: flex-end; gap: 8px;
    padding: 12px 16px; border-top: 1px solid #333;
  }
  button {
    padding: 7px 16px; border: none; border-radius: 4px;
    background: #3a3a5a; color: #ccc; cursor: pointer; font-size: 13px; min-height: 34px;
  }
  button:hover:not(:disabled) { background: #4a4a6a; }
  button:disabled { opacity: 0.5; cursor: default; }
  .primary-btn { background: #2a6; color: #fff; }
  .primary-btn:hover:not(:disabled) { background: #3b7; }
</style>
