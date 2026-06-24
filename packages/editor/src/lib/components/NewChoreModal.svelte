<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";

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

  function handleClose(): void {
    reset();
    onclose();
  }

  function handleFormKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleCreate(); }
  }
</script>

<Modal {open} title="New Chore" onclose={handleClose} width="360px">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="chore-form" onkeydown={handleFormKeydown} role="presentation">
    <div class="field">
      <label for="chore-name">Name</label>
      <!-- svelte-ignore a11y_autofocus -->
      <input id="chore-name" class="native-input" bind:value={name} placeholder="Chore name" autofocus />
    </div>

    <div class="field">
      <label for="chore-emoji">Emoji</label>
      <input id="chore-emoji" class="native-input emoji-input" bind:value={emoji} maxlength="4" />
    </div>

    <div class="field">
      <label>Repeat every</label>
      <div class="freq-row">
        <input type="number" class="native-input freq-n" bind:value={freqN} min="1" />
        <select class="native-input" bind:value={freqUnit}>
          <option value="days">days</option>
          <option value="weeks">weeks</option>
          <option value="months">months</option>
          <option value="years">years</option>
        </select>
      </div>
    </div>

    <div class="field">
      <label for="chore-due">First due</label>
      <input id="chore-due" type="date" class="native-input" bind:value={nextDue} />
    </div>

    <div class="field-row">
      <input type="checkbox" id="sfd" bind:checked={scheduleFromDue} />
      <label for="sfd" class="checkbox-label" title="Next due = planned date + period (not completion date + period)">
        Schedule from due date
      </label>
    </div>

    {#if error}<div class="error">{error}</div>{/if}
  </div>

  {#snippet footer()}
    <Button variant="secondary" onclick={handleClose}>Cancel</Button>
    <Button variant="primary" disabled={!name.trim() || saving} onclick={handleCreate}>
      {saving ? "Creating…" : "Create"}
    </Button>
  {/snippet}
</Modal>

<style>
  .chore-form { display: flex; flex-direction: column; gap: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field label { font-size: 11px; color: var(--text-muted); }
  .field-row { display: flex; align-items: center; gap: 8px; }
  .checkbox-label { font-size: 12px; color: var(--text-muted); cursor: pointer; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md);
    font-size: 13px; font-family: var(--font-sans); width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  input[type="date"].native-input { width: 160px; }
  .emoji-input { width: 80px; }
  .freq-row { display: flex; gap: 8px; }
  .freq-n { width: 80px; }
  .freq-row select { flex: 1; }

  .error { font-size: 11px; color: var(--danger); padding: 4px 0; }
</style>
