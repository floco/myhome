<script lang="ts">
  import type { createChoreStore, Chore } from "../choreStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import DatePicker from "./DatePicker.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type ChoreStore = Pick<ReturnType<typeof createChoreStore>, "updateChore" | "deleteChore" | "uploadAttachment" | "deleteAttachment">;

  interface Props {
    chore: Chore | null;
    store: ChoreStore;
    onclose: () => void;
  }

  let { chore, store, onclose }: Props = $props();

  let activeTab = $state<"info" | "media">("info");
  let draftName = $state("");
  let draftEmoji = $state("");
  let draftPeriodDays = $state(30);
  let draftNextDue = $state("");
  let draftScheduleFromDue = $state(false);
  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  $effect(() => {
    if (chore) {
      draftName = chore.name;
      draftEmoji = chore.emoji;
      draftPeriodDays = chore.periodDays;
      draftNextDue = chore.nextDueDate.slice(0, 10);
      draftScheduleFromDue = chore.scheduleFromDue;
      activeTab = "info";
      error = null;
    }
  });

  const mediaItems = $derived<MediaItem[]>(
    (chore?.attachments ?? []).map(fname => {
      const url = `/api/chores/${chore?.id}/attachments/${fname}`;
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  async function handleSave(): Promise<void> {
    if (!chore) return;
    if (!draftName.trim()) { error = "Name cannot be empty"; return; }
    saving = true; error = null;
    try {
      await store.updateChore(chore.id, {
        name: draftName.trim(),
        emoji: draftEmoji.trim() || "📋",
        periodDays: draftPeriodDays,
        nextDueDate: draftNextDue ? new Date(draftNextDue).toISOString() : chore.nextDueDate,
        scheduleFromDue: draftScheduleFromDue,
      });
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!chore) return;
    deleting = true;
    try { await store.deleteChore(chore.id); onclose(); }
    catch (e) { error = e instanceof Error ? e.message : "Delete failed"; deleting = false; }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!chore) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await store.uploadAttachment(chore.id, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Upload failed"; }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!chore) return;
    try { await store.deleteAttachment(chore.id, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : "Delete failed"; }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }
</script>

{#if chore}
  <Modal open={true} title={chore.emoji + " " + chore.name} onclose={onclose}>
    <Tabs
      tabs={[
        { id: "info", label: "Info" },
        { id: "media", label: (chore.attachments?.length ?? 0) > 0 ? `Media (${chore.attachments.length})` : "Media" },
      ]}
      active={activeTab}
      onchange={(id) => { activeTab = id as "info" | "media"; }}
    />

    {#if activeTab === "info"}
      <div class="edit-form">
        <label>Name
          <Input bind:value={draftName} placeholder="Chore name" />
        </label>
        <label>Emoji
          <input class="native-input emoji-field" bind:value={draftEmoji} placeholder="Emoji" maxlength="4" />
        </label>
        <label>Period (days)
          <input class="native-input" type="number" bind:value={draftPeriodDays} min="1" />
        </label>
        <label>Default due
          <DatePicker bind:value={draftNextDue} />
        </label>
        <div class="sfd-row">
          <input type="checkbox" id="sfd-modal" bind:checked={draftScheduleFromDue} />
          <label for="sfd-modal" title="Next due = planned date + period">Schedule from due date</label>
        </div>
        {#if error}<div class="form-error">{error}</div>{/if}
      </div>
    {:else}
      <div class="media-pane">
        <MediaGallery
          items={mediaItems}
          {uploading}
          uploadError={uploadError}
          onUpload={handleUpload}
          onDelete={handleDeleteAttachment}
          onItemClick={handleItemClick}
        />
        {#if uploadError}<div class="form-error">{uploadError}</div>{/if}
      </div>
    {/if}

    {#snippet footer()}
      <span class="spacer"></span>
      {#if confirmDelete}
        <span class="confirm-text">Delete this chore?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>{deleting ? "…" : "Confirm delete"}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>Cancel</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
      {#if activeTab === "info"}
        <Button variant="primary" disabled={saving} onclick={handleSave}>
          {saving ? "Saving…" : "Save"}
        </Button>
      {/if}
      <Button variant="secondary" onclick={onclose}>Cancel</Button>
    {/snippet}
  </Modal>
{/if}

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .edit-form { display: flex; flex-direction: column; gap: 10px; }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-faint); }
  .native-input {
    padding: 6px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text); font-size: 13px;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .emoji-field { width: 70px; }
  .native-input[type="number"] { width: 100px; }
  .sfd-row { display: flex; align-items: center; gap: 6px; font-size: 12px; }
  .sfd-row input[type="checkbox"] { width: auto; }

  .media-pane { min-height: 200px; }
  .form-error { font-size: 11px; color: var(--danger); margin-top: 4px; }
</style>
