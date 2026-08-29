<!-- packages/editor/src/lib/components/ContactModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createContactsStore, Contact, ContactUsageRef } from "../contactsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";

  type ContactsStore = ReturnType<typeof createContactsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    contact: Contact | null;
    store: ContactsStore;
    settingsStore: SettingsStore;
    onclose: () => void;
  }
  let { contact, store, settingsStore, onclose }: Props = $props();

  const isCreate = contact === null;

  let name = $state(contact?.name ?? "");
  let companyName = $state(contact?.companyName ?? "");
  let typeId = $state(contact?.typeId ?? settingsStore.contactTypes[0]?.id ?? "");
  let phone = $state(contact?.phone ?? "");
  let email = $state(contact?.email ?? "");
  let address = $state(contact?.address ?? "");
  let website = $state(contact?.website ?? "");
  let notes = $state(contact?.notes ?? "");
  let editingNotes = $state(isCreate);

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let usage = $state<ContactUsageRef[]>([]);
  let usageLoaded = $state(isCreate);

  $effect(() => {
    if (contact) {
      store.getUsage(contact.id).then((refs) => { usage = refs; usageLoaded = true; });
    }
  });

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = $_('contacts.modal.nameRequired'); return; }
    saving = true; error = null;
    const patch = {
      name: name.trim(),
      companyName: companyName.trim() || null,
      typeId,
      phone: phone.trim() || null,
      email: email.trim() || null,
      address: address.trim() || null,
      website: website.trim() || null,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createContact(patch);
      } else {
        await store.updateContact(contact!.id, patch);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('contacts.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!contact) return;
    deleting = true;
    try {
      await store.deleteContact(contact.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('contacts.modal.deleteFailed');
      deleting = false;
    }
  }
</script>

<Modal open={true} title={isCreate ? `＋ ${$_('contacts.modal.newContact')}` : $_('contacts.modal.editContact')} {onclose} width="520px">
  <div class="row">
    <label>{$_('contacts.modal.name')} *</label>
    <Input bind:value={name} placeholder={$_('contacts.modal.namePlaceholder')} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.companyName')}</label>
    <Input bind:value={companyName} placeholder={$_('contacts.modal.companyNamePlaceholder')} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.type')}</label>
    <select class="native-input" bind:value={typeId}>
      {#each settingsStore.contactTypes as t}
        <option value={t.id}>{t.name}</option>
      {/each}
    </select>
  </div>
  <div class="row-pair">
    <div class="row">
      <label>{$_('contacts.modal.phone')}</label>
      <Input bind:value={phone} />
    </div>
    <div class="row">
      <label>{$_('contacts.modal.email')}</label>
      <Input bind:value={email} />
    </div>
  </div>
  <div class="row">
    <label>{$_('contacts.modal.address')}</label>
    <Input bind:value={address} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.website')}</label>
    <Input bind:value={website} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.notes')}</label>
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder={$_('contacts.modal.notesPlaceholder')}
      minHeight="120px"
    />
    {#if editingNotes && !isCreate}
      <Button variant="secondary" onclick={() => { editingNotes = false; }}>{$_('works.modal.doneEditing')}</Button>
    {/if}
  </div>

  {#if !isCreate}
    <div class="row">
      <label>{$_('contacts.modal.usedIn')}</label>
      {#if !usageLoaded}
        <span class="usage-loading">…</span>
      {:else if usage.length === 0}
        <span class="usage-empty">{$_('contacts.modal.notUsed')}</span>
      {:else}
        <ul class="usage-list">
          {#each usage as ref}
            <li>{ref.label} <span class="usage-module">({ref.module})</span></li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}

  {#if error}<div class="modal-error">{error}</div>{/if}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">{$_('contacts.modal.confirm')}?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ {$_('contacts.modal.confirm')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button
          variant="danger"
          disabled={usage.length > 0}
          title={usage.length > 0 ? $_('contacts.modal.deleteBlockedByUsage') : undefined}
          onclick={() => { confirmDelete = true; }}
        >🗑 {$_('common.delete')}</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? $_('settings.security.saving') : isCreate ? $_('settings.security.create') : $_('common.save')}
    </Button>
  {/snippet}
</Modal>

<style>
  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .usage-list { margin: 0; padding-left: 18px; font-size: 12px; color: var(--text-muted); }
  .usage-module { color: var(--text-faint); }
  .usage-empty, .usage-loading { font-size: 12px; color: var(--text-faint); }
  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
