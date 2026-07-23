<!-- packages/editor/src/lib/components/TaskModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createBuildStore, BuildTask, ValidationStatus } from "../buildStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    task: BuildTask | null;
    store: BuildStore;
    onclose: () => void;
  }
  let { task, store, onclose }: Props = $props();

  function resolveLabel(key: string | null, override: string | null): string {
    if (override) return override;
    if (key) return $_(key);
    return "";
  }

  const resolvedTitle = task ? resolveLabel(task.titleKey, task.titleOverride) : "";
  const resolvedDescription = task ? resolveLabel(task.descriptionKey, task.descriptionOverride) : "";

  let title = $state(resolvedTitle);
  let description = $state(resolvedDescription);
  let status = $state<BuildTask["status"]>(task?.status ?? "not_started");
  let contractorId = $state(task?.contractorId ?? "");
  let plannedStartDate = $state(task?.plannedStartDate ?? "");
  let plannedDueDate = $state(task?.plannedDueDate ?? "");
  let actualCompletionDate = $state(task?.actualCompletionDate ?? "");
  let plannedCost = $state<string>(task?.plannedCost != null ? String(task.plannedCost) : "");
  let actualCost = $state<string>(task?.actualCost != null ? String(task.actualCost) : "");
  let validationRequired = $state(task?.validationRequired ?? false);
  let validationStatus = $state<ValidationStatus>(task?.validationStatus ?? "not_required");
  let notes = $state(task?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  const dependsOnTasks = $derived(
    task
      ? store.dependencies
          .filter((d) => d.successorTaskId === task!.id)
          .map((d) => store.tasks.find((t) => t.id === d.predecessorTaskId))
          .filter((t): t is BuildTask => !!t)
      : []
  );

  async function handleSave(): Promise<void> {
    if (!task) return;
    if (!title.trim()) { error = $_('build.modal.titleRequired'); return; }
    saving = true; error = null;
    try {
      await store.updateTask(task.id, {
        titleOverride: title.trim(),
        descriptionOverride: description.trim(),
        status,
        contractorId: contractorId || null,
        plannedStartDate: plannedStartDate || null,
        plannedDueDate: plannedDueDate || null,
        actualCompletionDate: actualCompletionDate || null,
        plannedCost: plannedCost ? parseFloat(plannedCost) || null : null,
        actualCost: actualCost ? parseFloat(actualCost) || null : null,
        validationRequired,
        validationStatus,
        notes: notes.trim(),
      });
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('build.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!task) return;
    deleting = true;
    try {
      await store.deleteTask(task.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('build.modal.deleteFailed');
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!task) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) await store.uploadAttachment(task.id, file);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('build.modal.uploadFailed');
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!task) return;
    try {
      await store.deleteAttachment(task.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('build.modal.deleteFailed');
    }
  }

  const currentTask = $derived(task ? (store.tasks.find((t) => t.id === task!.id) ?? task) : null);

  const mediaItems = $derived<MediaItem[]>(
    (currentTask?.attachments ?? []).map((name) => {
      const url = apiUrl(`/api/homes/${store.project?.id ?? ""}/build/tasks/${task!.id}/attachments/${name}`);
      const isPdf = name.toLowerCase().endsWith(".pdf");
      return { id: name, name, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );
</script>

{#if task}
  <Modal open={true} title={$_('build.modal.editTask')} {onclose} width="min(92vw, 820px)">
    <div class="row">
      <label>{$_('build.modal.title')} *</label>
      <input class="task-title-input native-input" bind:value={title} placeholder={$_('build.modal.titlePlaceholder')} />
    </div>
    <div class="row">
      <label>{$_('build.modal.description')}</label>
      <textarea class="native-input desc-area" bind:value={description} rows="4"></textarea>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.status')}</label>
        <select class="native-input" bind:value={status}>
          <option value="not_started">{$_('build.taskStatus.notStarted')}</option>
          <option value="ready">{$_('build.taskStatus.ready')}</option>
          <option value="in_progress">{$_('build.taskStatus.inProgress')}</option>
          <option value="waiting">{$_('build.taskStatus.waiting')}</option>
          <option value="blocked">{$_('build.taskStatus.blocked')}</option>
          <option value="completed">{$_('build.taskStatus.completed')}</option>
        </select>
      </div>
      <div class="row">
        <label>{$_('build.modal.contractor')}</label>
        <Input bind:value={contractorId} placeholder={$_('build.modal.contractorPlaceholder')} />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.plannedStart')}</label>
        <DatePicker bind:value={plannedStartDate} />
      </div>
      <div class="row">
        <label>{$_('build.modal.plannedDue')}</label>
        <DatePicker bind:value={plannedDueDate} />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.plannedCost')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={plannedCost} placeholder="0.00" />
      </div>
      <div class="row">
        <label>{$_('build.modal.actualCost')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={actualCost} placeholder="0.00" />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('build.modal.actualCompletion')}</label>
        <DatePicker bind:value={actualCompletionDate} />
      </div>
      <div class="row checkbox-row">
        <label><input type="checkbox" bind:checked={validationRequired} /> {$_('build.modal.validationRequired')}</label>
      </div>
    </div>
    {#if validationRequired}
      <div class="row validation-status-row">
        <label>{$_('build.modal.validationStatus')}</label>
        <select class="native-input" bind:value={validationStatus}>
          <option value="not_required">{$_('build.validationStatus.notRequired')}</option>
          <option value="pending_validation">{$_('build.validationStatus.pendingValidation')}</option>
          <option value="passed">{$_('build.validationStatus.passed')}</option>
          <option value="failed">{$_('build.validationStatus.failed')}</option>
        </select>
      </div>
    {/if}
    {#if dependsOnTasks.length > 0}
      <div class="row">
        <label>{$_('build.modal.dependsOn')}</label>
        <div class="dep-chips">
          {#each dependsOnTasks as dep (dep.id)}
            <span class="dep-chip">{resolveLabel(dep.titleKey, dep.titleOverride)}</span>
          {/each}
        </div>
      </div>
    {/if}
    <div class="row">
      <label>{$_('build.modal.notes')}</label>
      <textarea class="native-input desc-area" bind:value={notes} rows="3"></textarea>
    </div>

    <MediaGallery items={mediaItems} {uploading} {uploadError} onUpload={handleUpload} onDelete={handleDeleteAttachment} onItemClick={(i) => { lightboxIndex = i; lightboxOpen = true; }} />

    {#if error}<div class="modal-error">{error}</div>{/if}

    {#snippet footer()}
      {#if confirmDelete}
        <span class="confirm-text">{$_('build.modal.confirm')}?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ {$_('build.modal.confirm')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 {$_('common.delete')}</Button>
      {/if}
      <span class="spacer"></span>
      <Button variant="primary" disabled={saving} onclick={handleSave}>{$_('common.save')}</Button>
    {/snippet}
  </Modal>
{/if}

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  .checkbox-row { justify-content: center; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; width: 100%; box-sizing: border-box;
  }
  .desc-area { resize: vertical; white-space: pre-line; }
  .dep-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .dep-chip { font-size: 11px; padding: 2px 8px; border-radius: var(--radius-pill); background: var(--surface-alt); color: var(--text-muted); }
  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
