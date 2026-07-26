<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createInsuranceStore, InsurancePolicy } from "../insuranceStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createContactsStore } from "../contactsStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type InsuranceStore = ReturnType<typeof createInsuranceStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type ContactsStore = ReturnType<typeof createContactsStore>;

  interface Props {
    policy: InsurancePolicy | null;
    store: InsuranceStore;
    settingsStore: SettingsStore;
    contactsStore: ContactsStore;
    onclose: () => void;
  }

  let { policy, store, settingsStore, contactsStore, onclose }: Props = $props();

  const isCreate = policy === null;

  let activeTab = $state<"details" | "cost" | "coverage" | "alternatives">("details");
  let name = $state(policy?.name ?? "");
  let categoryId = $state(policy?.categoryId ?? settingsStore.insuranceCategories[0]?.id ?? "");
  let contactId = $state(policy?.contactId ?? "");
  let policyNumber = $state(policy?.policyNumber ?? "");
  let startDate = $state(policy?.startDate ?? "");
  let endDate = $state(policy?.endDate ?? "");
  let premiumAmount = $state<string>(policy?.premiumAmount != null ? String(policy.premiumAmount) : "");
  let premiumFrequency = $state<InsurancePolicy["premiumFrequency"]>(policy?.premiumFrequency ?? "annual");
  let includeInCosts = $state(policy?.includeInCosts ?? categoryId === "icat-home");
  $effect(() => {
    if (isCreate) {
      includeInCosts = categoryId === "icat-home";
    }
  });
  let coverageSummary = $state(policy?.coverageSummary ?? "");
  let conditionsUrl = $state(policy?.conditionsUrl ?? "");
  let alternatives = $state(policy?.alternatives ?? "");
  let notes = $state(policy?.notes ?? "");

  let editingNotes = $state(isCreate);
  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);

  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = $_('insurance.modal.nameRequired'); return; }
    if (!categoryId) { error = $_('insurance.modal.categoryRequired'); return; }
    saving = true; error = null;
    const patch = {
      name: name.trim(),
      categoryId,
      contactId: contactId || null,
      policyNumber: policyNumber.trim() || null,
      coverageSummary: coverageSummary.trim(),
      conditionsUrl: conditionsUrl.trim() || null,
      startDate: startDate || null,
      endDate: endDate || null,
      premiumAmount: premiumAmount ? parseFloat(premiumAmount) || null : null,
      premiumFrequency,
      includeInCosts,
      alternatives: alternatives.trim(),
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createPolicy(patch);
        onclose();
      } else {
        await store.updatePolicy(policy!.id, patch);
        editingNotes = false;
        onclose();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : $_('insurance.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!policy) return;
    deleting = true;
    try {
      await store.deletePolicy(policy.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('insurance.modal.deleteFailed');
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!policy) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) {
        await store.uploadAttachment(policy.id, file);
      }
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('insurance.modal.uploadFailed');
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!policy) return;
    try {
      await store.deleteAttachment(policy.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('insurance.modal.deleteFailed');
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }

  const currentPolicy = $derived(
    policy ? (store.policies.find(p => p.id === policy.id) ?? policy) : null
  );
  const attachmentCount = $derived(currentPolicy?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentPolicy?.attachments ?? []).map(fname => {
      const homeId = homesStore.activeHomeId;
      const url = apiUrl(`/api/homes/${homeId}/insurance/${policy!.id}/attachments/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return {
        id: fname,
        name: fname,
        url,
        thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url,
        type: isPdf ? "document" : "image",
      };
    })
  );
</script>

<Modal open={true} title={isCreate ? `＋ ${$_('insurance.modal.newPolicy')}` : $_('insurance.modal.editPolicy')} {onclose} width="min(92vw, 820px)">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "details"} onclick={() => { activeTab = "details"; }}>{$_('chores.editModal.info')}</button>
    <button class="tab" class:active={activeTab === "cost"} onclick={() => { activeTab = "cost"; }}>{$_('insurance.modal.costTab')}</button>
    <button class="tab" class:active={activeTab === "coverage"} onclick={() => { activeTab = "coverage"; }}>{$_('insurance.modal.coverageTab')}</button>
    <button class="tab" class:active={activeTab === "alternatives"} onclick={() => { activeTab = "alternatives"; }}>{$_('insurance.modal.alternativesTab')}</button>
  </div>

  {#if activeTab === "details"}
    <div class="row">
      <label>{$_('insurance.page.name')} *</label>
      <Input bind:value={name} placeholder={$_('insurance.modal.namePlaceholder')} />
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('costs.page.category')} *</label>
        <select class="native-input" bind:value={categoryId}>
          {#each settingsStore.insuranceCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
      <div class="row">
        <label>{$_('insurance.modal.policyNumber')}</label>
        <Input bind:value={policyNumber} placeholder={$_('insurance.modal.policyNumberPlaceholder')} />
      </div>
    </div>
    <div class="row">
      <label>{$_('costs.entryModal.supplier')}</label>
      <select class="native-input" bind:value={contactId}>
        <option value="">{$_('works.modal.noneOption')}</option>
        {#each contactsStore.contacts as c}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('insurance.page.startDate')}</label>
        <DatePicker bind:value={startDate} />
      </div>
      <div class="row">
        <label>{$_('insurance.page.endDate')}</label>
        <DatePicker bind:value={endDate} />
      </div>
    </div>
  {:else if activeTab === "cost"}
    <div class="row-pair">
      <div class="row">
        <label>{$_('insurance.modal.premiumAmount')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={premiumAmount} placeholder="0.00" />
      </div>
      <div class="row">
        <label>{$_('insurance.modal.premiumFrequency')}</label>
        <select class="native-input" bind:value={premiumFrequency}>
          <option value="monthly">{$_('insurance.frequency.monthly')}</option>
          <option value="quarterly">{$_('insurance.frequency.quarterly')}</option>
          <option value="annual">{$_('insurance.frequency.annual')}</option>
          <option value="other">{$_('insurance.frequency.other')}</option>
        </select>
      </div>
    </div>
    <label class="checkbox-row">
      <input type="checkbox" bind:checked={includeInCosts} />
      {$_('insurance.modal.includeInCosts')}
    </label>
    <p class="hint">{$_('insurance.modal.includeInCostsHint')}</p>
  {:else if activeTab === "coverage"}
    <div class="row">
      <label>{$_('insurance.modal.coverageSummary')}</label>
      <textarea class="native-input desc-area" bind:value={coverageSummary} placeholder={$_('insurance.modal.coverageSummaryPlaceholder')} rows="3"></textarea>
    </div>
    <div class="row">
      <label>{$_('insurance.modal.conditionsUrl')}</label>
      <Input bind:value={conditionsUrl} placeholder="https://…" />
    </div>
    {#if isCreate}
      <p class="hint">{$_('insurance.modal.attachAfterCreate')}</p>
    {:else}
      <MediaGallery
        items={mediaItems}
        {uploading}
        {uploadError}
        onUpload={handleUpload}
        onDelete={handleDeleteAttachment}
        onItemClick={handleItemClick}
      />
    {/if}
  {:else}
    <div class="row">
      <label>{$_('insurance.modal.alternatives')}</label>
      <textarea class="native-input desc-area" bind:value={alternatives} placeholder={$_('insurance.modal.alternativesPlaceholder')} rows="4"></textarea>
    </div>
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder={$_('works.modal.notesPlaceholder')}
      minHeight="140px"
    />
    {#if editingNotes && !isCreate}
      <Button variant="secondary" onclick={() => { editingNotes = false; }}>{$_('works.modal.doneEditing')}</Button>
    {/if}
  {/if}

  {#if error}<div class="modal-error">{error}</div>{/if}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ {$_('works.modal.confirm')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 {$_('common.delete')}</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? $_('settings.security.saving') : isCreate ? $_('settings.security.create') : $_('common.save')}
    </Button>
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab {
    padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans);
  }
  .tab:hover { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }

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
  .desc-area { resize: vertical; min-height: 48px; }

  .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text); margin-bottom: 4px; cursor: pointer; }
  .hint { font-size: 11px; color: var(--text-faint); margin: 0 0 var(--space-3); }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
