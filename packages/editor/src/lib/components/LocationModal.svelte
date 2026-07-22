<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Location } from "../locationsStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";

  interface Props {
    location: Location | null;
    onsave: (data: { name: string; emoji: string }) => void;
    onclose: () => void;
  }
  let { location, onsave, onclose }: Props = $props();

  const isCreate = location === null;

  let name = $state(location?.name ?? "");
  let emoji = $state(location?.emoji ?? "📍");

  function handleSave(): void {
    const trimmed = name.trim();
    if (!trimmed) return;
    onsave({ name: trimmed, emoji });
    onclose();
  }
</script>

<Modal open={true} title={isCreate ? $_('locations.modal.addLocation') : $_('locations.modal.editLocation')} {onclose} width="360px">
  {#snippet children()}
    <div class="form">
      <div class="row">
        <div class="field short">
          <label>{$_('locations.modal.flag')}</label>
          <EmojiPicker bind:value={emoji} flags={true} />
        </div>
        <div class="field grow">
          <label>{$_('chores.editModal.name')} *</label>
          <Input bind:value={name} placeholder={$_('locations.modal.namePlaceholder')} />
        </div>
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
  .row { display: flex; gap: var(--space-2); }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field.grow { flex: 1; }
  .field.short { flex-shrink: 0; }
  label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.05em; }
</style>
