<script lang="ts">
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

<Modal open={true} title={isCreate ? "Add criterion" : "Edit criterion"} {onclose} width="400px">
  {#snippet children()}
    <div class="form">
      <div class="field">
        <label>Name *</label>
        <Input bind:value={name} placeholder="e.g. Cost of Living" />
      </div>
      <div class="field">
        <label>Description</label>
        <textarea bind:value={description} rows="3" class="native-textarea" placeholder="Optional notes…"></textarea>
      </div>
      <div class="field">
        <label>Weight</label>
        <select class="native-select" bind:value={weight}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>
    </div>
  {/snippet}

  {#snippet footer()}
    <Button variant="ghost" onclick={onclose}>Cancel</Button>
    <Button onclick={handleSave} disabled={!name.trim()}>{isCreate ? "Add" : "Save"}</Button>
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
