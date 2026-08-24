<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createChoreStore, Chore } from "../choreStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import ScheduleAnchorPicker from "./ui/ScheduleAnchorPicker.svelte";
  import DatePicker from "./ui/DatePicker.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import ScheduleEditor from "./ScheduleEditor.svelte";
  import ChoreCompleteModal from "./ChoreCompleteModal.svelte";
  import { polygonCentroid } from "@myhome/geometry";
  import type { Point } from "@myhome/geometry";
  import { formatDate } from "../dateFormat";

  type ChoreStore = Pick<ReturnType<typeof createChoreStore>, "updateChore" | "deleteChore" | "uploadAttachment" | "deleteAttachment" | "getCompletionsForChore" | "assignments" | "deleteCompletion" | "createAssignment" | "updateAssignmentLabel" | "deleteAssignment" | "delayAssignment" | "completeAssignment" | "completeChore" | "previewNextDue">;

  interface Props {
    chore: Chore | null;
    store: ChoreStore;
    rooms: Array<{ id: string; label: string; polygon: Point[] | null }>;
    onclose: () => void;
    onplaceonmap?: (choreId: string) => void;
  }

  let { chore, store, rooms, onclose, onplaceonmap }: Props = $props();

  let activeTab = $state<"info" | "assignments" | "media" | "history">("info");
  let draftName = $state("");
  let draftEmoji = $state("");
  let draftPeriodDays = $state(30);
  let draftFrequencyType = $state("interval");
  let draftFrequency = $state(1);
  let draftFrequencyMetadata = $state<Record<string, unknown>>({});
  let draftScheduleValid = $state(true);
  let draftNextDue = $state("");
  let draftScheduleFromDue = $state(false);
  let draftDescription = $state("");
  let nextDuePreview = $state("");
  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);
  let newAssignmentRoomId = $state("");
  let newAssignmentLabel = $state("");
  let completing = $state<{ kind: "chore" | "assignment"; id: string; title: string } | null>(null);

  const history = $derived(
    chore
      ? store.getCompletionsForChore(chore.id).slice().sort((a, b) => b.completedAt.localeCompare(a.completedAt))
      : []
  );
  const assignmentsForChore = $derived(chore ? store.assignments.filter((a) => a.choreId === chore.id) : []);
  const sortedRooms = $derived([...rooms].sort((a, b) => a.label.localeCompare(b.label)));
  let deletingCompletion = $state<string | null>(null);

  function getRoomName(assignmentId: string | null): string {
    if (!assignmentId) return `🏠 ${$_('chores.list.wholeHouse')}`;
    const assignment = store.assignments.find((a) => a.id === assignmentId);
    if (!assignment?.roomId) return `🏠 ${$_('chores.list.wholeHouse')}`;
    return rooms.find((r) => r.id === assignment.roomId)?.label ?? $_('chores.list.unknownRoom');
  }

  function getAssignmentLabel(assignmentId: string | null): string | null {
    if (!assignmentId) return null;
    return store.assignments.find((a) => a.id === assignmentId)?.label ?? null;
  }

  async function handleLabelBlur(assignmentId: string, value: string): Promise<void> {
    const trimmed = value.trim();
    const current = store.assignments.find((a) => a.id === assignmentId)?.label ?? "";
    if (trimmed === current) return;
    await store.updateAssignmentLabel(assignmentId, trimmed);
  }

  async function handleAddAssignment(): Promise<void> {
    if (!chore || !newAssignmentRoomId) return;
    const room = rooms.find((r) => r.id === newAssignmentRoomId);
    const position = room?.polygon ? polygonCentroid(room.polygon) : null;
    await store.createAssignment({
      choreId: chore.id,
      roomId: newAssignmentRoomId,
      position,
      nextDueDate: "",
      label: newAssignmentLabel.trim() || null,
    });
    newAssignmentRoomId = "";
    newAssignmentLabel = "";
  }

  async function confirmCompleteAssignment(notes: string, completedOn?: string): Promise<void> {
    if (!completing) return;
    const { kind, id } = completing;
    completing = null;
    if (kind === "chore") {
      if (completedOn) await store.completeChore(id, notes, completedOn);
      else await store.completeChore(id, notes);
    } else {
      if (completedOn) await store.completeAssignment(id, notes, completedOn);
      else await store.completeAssignment(id, notes);
    }
  }

  async function handleDeleteCompletion(id: string): Promise<void> {
    deletingCompletion = id;
    try { await store.deleteCompletion(id); }
    catch (e) { error = e instanceof Error ? e.message : $_('chores.editModal.deleteFailed'); }
    finally { deletingCompletion = null; }
  }

  $effect.pre(() => {
    if (chore) {
      draftName = chore.name;
      draftEmoji = chore.emoji;
      draftPeriodDays = chore.periodDays;
      draftFrequencyType = chore.frequencyType;
      draftFrequency = chore.frequency;
      draftFrequencyMetadata = chore.frequencyMetadata;
      draftNextDue = chore.nextDueDate.slice(0, 10);
      draftScheduleFromDue = chore.scheduleFromDue;
      draftDescription = chore.description ?? "";
      activeTab = "info";
      newAssignmentRoomId = "";
      newAssignmentLabel = "";
      error = null;
    }
  });

  $effect(() => {
    if (!chore || !draftScheduleValid) { nextDuePreview = ""; return; }
    const params = {
      frequencyType: draftFrequencyType,
      frequency: draftFrequency,
      frequencyMetadata: draftFrequencyMetadata,
      scheduleFromDue: draftScheduleFromDue,
      nextDueDate: draftNextDue ? new Date(draftNextDue).toISOString() : "",
      periodDays: draftPeriodDays,
      choreId: chore.id,
    };
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const result = await store.previewNextDue(params);
        if (!cancelled) nextDuePreview = result;
      } catch {
        if (!cancelled) nextDuePreview = "";
      }
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  });

  const mediaItems = $derived<MediaItem[]>(
    (chore?.attachments ?? []).map(fname => {
      const url = apiUrl(`/api/homes/${homesStore.activeHomeId}/attachments/chores/${chore?.id}/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );

  async function handleSave(): Promise<void> {
    if (!chore) return;
    if (!draftName.trim()) { error = $_('chores.editModal.nameEmpty'); return; }
    if (!draftScheduleValid) return;
    saving = true; error = null;
    try {
      await store.updateChore(chore.id, {
        name: draftName.trim(),
        emoji: draftEmoji.trim() || "📋",
        periodDays: draftPeriodDays,
        frequencyType: draftFrequencyType,
        frequency: draftFrequency,
        frequencyMetadata: draftFrequencyMetadata,
        nextDueDate: draftNextDue ? new Date(draftNextDue).toISOString() : chore.nextDueDate,
        scheduleFromDue: draftScheduleFromDue,
        description: draftDescription,
      });
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('chores.editModal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!chore) return;
    deleting = true;
    try { await store.deleteChore(chore.id); onclose(); }
    catch (e) { error = e instanceof Error ? e.message : $_('chores.editModal.deleteFailed'); deleting = false; }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!chore) return;
    uploading = true; uploadError = null;
    try { for (const file of files) await store.uploadAttachment(chore.id, file); }
    catch (err) { uploadError = err instanceof Error ? err.message : $_('chores.editModal.uploadFailed'); }
    finally { uploading = false; }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!chore) return;
    try { await store.deleteAttachment(chore.id, id); }
    catch (err) { uploadError = err instanceof Error ? err.message : $_('chores.editModal.deleteFailed'); }
  }

  function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }
</script>

{#if chore}
  <Modal open={true} title={chore.emoji + " " + chore.name} onclose={onclose}>
    <Tabs
      tabs={[
        { id: "info", label: $_('chores.editModal.info') },
        { id: "assignments", label: assignmentsForChore.length > 0 ? $_('chores.editModal.assignmentsCount', { values: { n: assignmentsForChore.length } }) : $_('chores.editModal.assignments') },
        { id: "media", label: (chore.attachments?.length ?? 0) > 0 ? $_('chores.editModal.mediaCount', { values: { n: chore.attachments.length } }) : $_('chores.editModal.media') },
        { id: "history", label: history.length > 0 ? $_('chores.editModal.historyCount', { values: { n: history.length } }) : $_('chores.editModal.history') },
      ]}
      active={activeTab}
      onchange={(id) => { activeTab = id as "info" | "assignments" | "media" | "history"; }}
    />

    {#if activeTab === "info"}
      <div class="edit-form">
        <div class="name-emoji-row">
          <label class="emoji-field">{$_('chores.editModal.emoji')}
            <EmojiPicker bind:value={draftEmoji} />
          </label>
          <label class="name-row-field">{$_('chores.editModal.name')}
            <Input bind:value={draftName} placeholder={$_('chores.editModal.choreName')} />
          </label>
        </div>
        {#key chore.id}
          <ScheduleEditor
            bind:frequencyType={draftFrequencyType}
            bind:frequency={draftFrequency}
            bind:frequencyMetadata={draftFrequencyMetadata}
            bind:periodDays={draftPeriodDays}
            bind:valid={draftScheduleValid}
          />
        {/key}
        <label>{$_('chores.editModal.defaultDue')}
          <DatePicker bind:value={draftNextDue} />
        </label>
        <ScheduleAnchorPicker bind:scheduleFromDue={draftScheduleFromDue} idPrefix="edit-sfd" />
        {#if nextDuePreview}
          <div class="next-due-preview">
            <span class="next-due-preview-label">{$_('chores.editModal.nextDueComputed')}</span>
            <span class="next-due-preview-value">{formatDate(nextDuePreview)}</span>
          </div>
        {/if}
        <label>{$_('chores.editModal.notes')}
          <textarea class="native-input notes-field" bind:value={draftDescription} placeholder={$_('chores.editModal.notesPlaceholder')} rows="4"></textarea>
        </label>
        {#if error}<div class="form-error">{error}</div>{/if}
      </div>
    {:else if activeTab === "assignments"}
      <div class="assignments-pane">
        {#if onplaceonmap}
          <Button variant="secondary" onclick={() => { onplaceonmap!(chore!.id); }}>📍 {$_('chores.editModal.placeOnMap')}</Button>
        {/if}
        {#if assignmentsForChore.length === 0}
          <div class="no-assignments">{$_('chores.page.notAssigned')}</div>
        {:else}
          {#each assignmentsForChore as a (a.id)}
            <div class="assignment-row">
              <span class="assign-where">{a.roomId ? (rooms.find((r) => r.id === a.roomId)?.label ?? $_('chores.list.unknownRoom')) : `🏠 ${$_('chores.list.wholeHouse')}`}</span>
              <input
                class="native-input assign-label-input"
                placeholder={$_('chores.editModal.labelPlaceholder')}
                value={a.label ?? ""}
                onblur={(e) => handleLabelBlur(a.id, (e.target as HTMLInputElement).value)}
              />
              <span class="assign-due">{$_('chores.badgePopup.due')}: {formatDate(a.nextDueDate)}</span>
              <div class="assignment-actions">
                <button class="icon-btn" title={$_('chores.row.markDone')} onclick={() => { completing = { kind: "assignment", id: a.id, title: `${chore.emoji} ${chore.name}` }; }}>✓</button>
                <button class="icon-btn" title={$_('chores.page.delayByWeek')} onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
                <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
              </div>
            </div>
          {/each}
        {/if}
        <div class="add-assignment-row">
          <select class="native-input" bind:value={newAssignmentRoomId}>
            <option value="">{$_('chores.editModal.selectRoom')}</option>
            {#each sortedRooms as room}
              <option value={room.id}>{room.label}</option>
            {/each}
          </select>
          <input class="native-input assign-label-input" placeholder={$_('chores.editModal.labelPlaceholder')} bind:value={newAssignmentLabel} />
          <Button variant="secondary" disabled={!newAssignmentRoomId} onclick={handleAddAssignment}>{$_('chores.editModal.addAssignment')}</Button>
        </div>
      </div>
    {:else if activeTab === "media"}
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
    {:else if activeTab === "history"}
      <div class="history-pane">
        {#if history.length === 0}
          <div class="no-history">{$_('chores.editModal.noCompletions')}</div>
        {:else}
          {#each history as rec (rec.id)}
            {@const label = getAssignmentLabel(rec.assignmentId)}
            <div class="history-row">
              <span class="hist-room">{getRoomName(rec.assignmentId)}{#if label} <span class="hist-label">({label})</span>{/if}</span>
              <span class="hist-date">{formatDate(rec.completedAt)}</span>
              {#if rec.scheduledDue}<span class="hist-due">{$_('chores.editModal.dueOn', { values: { date: formatDate(rec.scheduledDue) } })}</span>{/if}
              {#if rec.notes}<span class="hist-notes">{rec.notes}</span>{/if}
              <button class="hist-del" disabled={deletingCompletion === rec.id} title={$_('chores.editModal.deleteRecord')} onclick={() => handleDeleteCompletion(rec.id)}>🗑</button>
            </div>
          {/each}
        {/if}
      </div>
    {/if}

    {#snippet footer()}
      {#if !confirmDelete}
        <button class="icon-btn footer-complete-all" title={$_('chores.page.markAllDone')} onclick={() => { completing = { kind: "chore", id: chore!.id, title: `${chore!.emoji} ${chore!.name}` }; }}>✓</button>
        {#if activeTab !== "assignments"}
          <button class="icon-btn footer-go-to-assignments" title={$_('chores.editModal.goToAssignments')} onclick={() => { activeTab = "assignments"; }}>→</button>
        {/if}
      {/if}
      <span class="spacer"></span>
      {#if confirmDelete}
        <span class="confirm-text">{$_('chores.editModal.deleteThisChore')}</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>{deleting ? "…" : $_('chores.editModal.confirmDelete')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>{$_('common.cancel')}</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 {$_('common.delete')}</Button>
        <Button variant="secondary" onclick={onclose}>{$_('common.cancel')}</Button>
        <Button variant="primary" disabled={saving || !draftScheduleValid} onclick={handleSave}>
          {saving ? $_('settings.security.saving') : $_('common.save')}
        </Button>
      {/if}
    {/snippet}
  </Modal>
{/if}

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

{#if completing}
  <ChoreCompleteModal title={completing.title} onclose={() => { completing = null; }} onconfirm={confirmCompleteAssignment} />
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
  .name-emoji-row { display: flex; gap: 8px; align-items: flex-end; }
  .name-emoji-row .emoji-field { width: 70px; flex-shrink: 0; }
  .name-emoji-row .name-row-field { flex: 1; min-width: 0; }
  .next-due-preview {
    display: flex; align-items: center; gap: 6px; font-size: 12px;
    padding: 6px 8px; border-radius: var(--radius-sm); background: var(--surface-alt);
  }
  .next-due-preview-label { color: var(--text-faint); }
  .next-due-preview-value { color: var(--text); font-weight: 500; }
  .notes-field { resize: vertical; min-height: 72px; font-family: inherit; line-height: 1.4; }

  .media-pane { min-height: 200px; }
  .form-error { font-size: 11px; color: var(--danger); margin-top: 4px; }
  .history-pane { min-height: 160px; }
  .no-history { font-size: 12px; color: var(--text-faint); font-style: italic; padding: 12px 0; }
  .history-row { display: flex; align-items: baseline; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 12px; flex-wrap: wrap; }
  .history-row:last-child { border-bottom: none; }
  .hist-room { color: var(--text); white-space: nowrap; font-weight: 500; min-width: 90px; }
  .hist-date { color: var(--text-muted); white-space: nowrap; }
  .hist-due { color: var(--text-faint); white-space: nowrap; font-size: 11px; }
  .hist-notes { color: var(--text-muted); font-style: italic; font-size: 11px; flex: 1; }
  .hist-del { margin-left: auto; background: none; border: none; cursor: pointer; color: var(--text-faint); font-size: 11px; padding: 0 2px; line-height: 1; opacity: 0.5; }
  .hist-del:hover { opacity: 1; color: var(--danger); }
  .hist-label { color: var(--text-faint); font-weight: 400; margin-left: 4px; }

  .assignments-pane { min-height: 160px; display: flex; flex-direction: column; gap: 8px; }
  .no-assignments { font-size: 11px; color: var(--text-faint); font-style: italic; padding: 12px 0; }
  .assignment-row { display: flex; align-items: center; gap: 8px; font-size: 12px; flex-wrap: wrap; padding: 6px 0; border-bottom: 1px solid var(--border); }
  .assign-where { flex: 1; min-width: 80px; color: var(--text-muted); }
  .assign-label-input { flex: 1; min-width: 100px; }
  .assign-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .assignment-actions { display: flex; gap: 4px; flex-shrink: 0; }
  .add-assignment-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding-top: 4px; }
  .add-assignment-row select { flex: 1; min-width: 120px; }
  .icon-btn {
    padding: 6px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 13px;
    min-height: 30px;
  }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .icon-btn.danger:hover { color: var(--danger); }
</style>
