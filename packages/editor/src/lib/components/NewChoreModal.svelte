<script lang="ts">
  import { _, locale } from "svelte-i18n";
  import type { createChoreStore } from "../choreStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import ScheduleAnchorPicker from "./ui/ScheduleAnchorPicker.svelte";
  import ScheduleEditor from "./ScheduleEditor.svelte";
  import { parseScheduleText } from "../scheduleParser";

  type ChoreStore = Pick<ReturnType<typeof createChoreStore>, "createChore">;

  interface Props {
    open: boolean;
    store: ChoreStore;
    onclose: () => void;
  }

  let { open, store, onclose }: Props = $props();

  let name = $state("");
  let emoji = $state("📋");
  let quickAddText = $state("");
  let frequencyType = $state("interval");
  let frequency = $state(30);
  let frequencyMetadata = $state<Record<string, unknown>>({ unit: "days" });
  let periodDays = $state(30);
  let scheduleValid = $state(true);
  let resetKey = $state(0);
  let nextDue = $state(new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));
  let scheduleFromDue = $state(false);
  let saving = $state(false);
  let error = $state("");

  function handleParse(): void {
    const loc = ($locale ?? "en").startsWith("fr") ? "fr" : "en";
    const result = parseScheduleText(quickAddText, loc);
    if (!result) {
      name = quickAddText.trim();
      return;
    }
    name = result.name;
    frequencyType = result.schedule.frequencyType;
    frequency = result.schedule.frequency;
    frequencyMetadata = result.schedule.frequencyMetadata;
    resetKey += 1;
  }

  async function handleCreate(): Promise<void> {
    if (!name.trim() || !scheduleValid) return;
    saving = true;
    error = "";
    try {
      await store.createChore({
        name: name.trim(),
        emoji: emoji.trim() || "📋",
        periodDays,
        frequencyType,
        frequency,
        frequencyMetadata,
        scheduleFromDue,
        nextDueDate: new Date(nextDue).toISOString(),
        description: "",
        donetickId: null,
      });
      reset();
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('chores.newModal.failedToCreate');
    } finally {
      saving = false;
    }
  }

  function reset(): void {
    name = ""; emoji = "📋"; quickAddText = "";
    frequencyType = "interval"; frequency = 30; frequencyMetadata = { unit: "days" }; periodDays = 30;
    resetKey += 1;
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

<Modal {open} title={$_('chores.newModal.title')} onclose={handleClose} width="360px">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="chore-form" onkeydown={handleFormKeydown} role="presentation">
    <div class="field">
      <label for="chore-quickadd">{$_('chores.quickAdd.label')}</label>
      <div class="quickadd-row">
        <!-- svelte-ignore a11y_autofocus -->
        <input id="chore-quickadd" class="native-input" bind:value={quickAddText} placeholder={$_('chores.quickAdd.placeholder')} autofocus />
        <Button variant="secondary" onclick={handleParse}>{$_('chores.quickAdd.parse')}</Button>
      </div>
    </div>

    <div class="name-emoji-row">
      <div class="field emoji-input">
        <label for="chore-emoji">{$_('chores.editModal.emoji')}</label>
        <EmojiPicker bind:value={emoji} />
      </div>

      <div class="field name-row-field">
        <label for="chore-name">{$_('chores.editModal.name')}</label>
        <input id="chore-name" class="native-input" bind:value={name} placeholder={$_('chores.editModal.choreName')} />
      </div>
    </div>

    {#key resetKey}
      <ScheduleEditor
        bind:frequencyType
        bind:frequency
        bind:frequencyMetadata
        bind:periodDays
        bind:valid={scheduleValid}
      />
    {/key}

    <div class="field">
      <label for="chore-due">{$_('chores.newModal.firstDue')}</label>
      <input id="chore-due" type="date" class="native-input" bind:value={nextDue} />
    </div>

    <div class="field">
      <ScheduleAnchorPicker bind:scheduleFromDue idPrefix="new-sfd" />
    </div>

    {#if error}<div class="error">{error}</div>{/if}
  </div>

  {#snippet footer()}
    <Button variant="secondary" onclick={handleClose}>{$_('common.cancel')}</Button>
    <Button variant="primary" disabled={!name.trim() || !scheduleValid || saving} onclick={handleCreate}>
      {saving ? $_('chores.newModal.creating') : $_('settings.security.create')}
    </Button>
  {/snippet}
</Modal>

<style>
  .chore-form { display: flex; flex-direction: column; gap: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field label { font-size: 11px; color: var(--text-muted); }
  .quickadd-row { display: flex; gap: 8px; align-items: center; }
  .quickadd-row .native-input { flex: 1; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md);
    font-size: 13px; font-family: var(--font-sans); width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  input[type="date"].native-input { width: 160px; }
  .name-emoji-row { display: flex; gap: 8px; align-items: flex-end; }
  .name-emoji-row .emoji-input { flex-shrink: 0; }
  .name-emoji-row .name-row-field { flex: 1; min-width: 0; }
  .emoji-input { width: 80px; }

  .error { font-size: 11px; color: var(--danger); padding: 4px 0; }
</style>
