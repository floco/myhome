<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { LocationCriterion, Weight } from "../locationsStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";

  interface Props {
    criterion: LocationCriterion | null;
    onsave: (data: { name: string; description: string; weight: Weight }) => void;
    onclose: () => void;
  }
  let { criterion, onsave, onclose }: Props = $props();

  const isCreate = criterion === null;

  let name = $state(criterion?.name ?? "");
  let description = $state(criterion?.description ?? "");
  let weight = $state<Weight>(criterion?.weight ?? "medium");

  function handleSave(): void {
    const trimmed = name.trim();
    if (!trimmed) return;
    onsave({ name: trimmed, description, weight });
    onclose();
  }
</script>

<Modal open={true} title={isCreate ? $_('locations.criterionModal.addCriterion') : $_('locations.criterionModal.editCriterion')} {onclose} width="400px">
  {#snippet children()}
    <div class="form">
      <div class="field">
        <label>{$_('chores.editModal.name')} *</label>
        <Input bind:value={name} placeholder={$_('locations.criterionModal.namePlaceholder')} />
      </div>
      <div class="field">
        <label>{$_('works.modal.description')}</label>
        <textarea bind:value={description} rows="3" class="native-textarea" placeholder={$_('inventory.modal.notesPlaceholder')}></textarea>
      </div>
      <div class="field">
        <label>{$_('locations.criterionModal.weight')}</label>
        <select class="native-select" bind:value={weight}>
          <option value="low">{$_('locations.criterionModal.low')}</option>
          <option value="medium">{$_('locations.criterionModal.medium')}</option>
          <option value="high">{$_('locations.criterionModal.high')}</option>
        </select>
      </div>
    </div>
  {/snippet}

  {#snippet footer()}
    <Button variant="ghost" onclick={onclose}>{$_('common.cancel')}</Button>
    <Button onclick={handleSave} disabled={!name.trim()}>{isCreate ? $_('common.add') : $_('common.save')}</Button>
  {/snippet}
</Modal>

<style>
  .form { display: flex; flex-direction: column; gap: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; }
  .native-select, .native-textarea {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 10px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); width: 100%; box-sizing: border-box;
  }
  .native-select:focus, .native-textarea:focus { outline: none; border-color: var(--accent); }
  .native-textarea { resize: vertical; }
</style>
