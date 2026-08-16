<!-- packages/editor/src/lib/components/ChoreCompleteModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import DatePicker from "./ui/DatePicker.svelte";
  import { todayIso } from "../dateFormat";

  interface Props {
    title: string;
    onclose: () => void;
    onconfirm: (notes: string, completedOn?: string) => void;
  }
  let { title, onclose, onconfirm }: Props = $props();

  let notes = $state("");
  let completedOn = $state(todayIso());

  function confirm(): void {
    if (completedOn === todayIso()) onconfirm(notes);
    else onconfirm(notes, completedOn);
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter") confirm();
  }
</script>

<Modal open={true} {title} {onclose} width="360px">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="complete-form" onkeydown={handleKeydown}>
    <label>{$_('chores.completeModal.completedOn')}
      <DatePicker bind:value={completedOn} max={todayIso()} />
    </label>
    <label>{$_('chores.completeModal.notes')}
      <Input bind:value={notes} placeholder={$_('chores.row.notePlaceholder')} />
    </label>
  </div>
  {#snippet footer()}
    <Button variant="secondary" onclick={onclose}>{$_('common.cancel')}</Button>
    <Button variant="primary" onclick={confirm}>{$_('chores.completeModal.confirm')}</Button>
  {/snippet}
</Modal>

<style>
  .complete-form { display: flex; flex-direction: column; gap: var(--space-3); }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-faint); }
</style>
