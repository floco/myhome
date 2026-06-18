<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    assigningChoreId: string | null;
    onAssignToRoom: (choreId: string) => void;
    onCancelAssign: () => void;
  }

  let { store, assigningChoreId, onAssignToRoom, onCancelAssign }: Props = $props();

  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await store.importFromDonetick(importToken.trim());
      importStatus = "done";
      importToken = "";
      showImportInput = false;
    } catch {
      importStatus = "error";
    }
  }

  let showNewForm = $state(false);
  let newName = $state("");
  let newEmoji = $state("📋");
  let newPeriodDays = $state(30);
  let newNextDue = $state(new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));

  async function handleCreate(): Promise<void> {
    if (!newName.trim()) return;
    await store.createChore({
      name: newName.trim(),
      emoji: newEmoji.trim() || "📋",
      periodDays: newPeriodDays,
      nextDueDate: new Date(newNextDue).toISOString(),
      description: "",
      donetickId: null,
    });
    showNewForm = false;
    newName = "";
    newEmoji = "📋";
    newPeriodDays = 30;
    newNextDue = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  }

  let editingId = $state<string | null>(null);
  let editName = $state("");
  let editEmoji = $state("");
  let editPeriodDays = $state(30);
  let editNextDue = $state("");

  function startEdit(chore: Chore): void {
    editingId = chore.id;
    editName = chore.name;
    editEmoji = chore.emoji;
    editPeriodDays = chore.periodDays;
    editNextDue = chore.nextDueDate.slice(0, 10);
  }

  async function handleUpdate(): Promise<void> {
    if (!editingId) return;
    await store.updateChore(editingId, {
      name: editName.trim(),
      emoji: editEmoji.trim() || "📋",
      periodDays: editPeriodDays,
      nextDueDate: new Date(editNextDue).toISOString(),
    });
    editingId = null;
  }

  const houseChores = $derived(
    store.houseAssignments().map((a) => ({
      assignment: a,
      chore: store.chores.find((c) => c.id === a.choreId),
    })).filter((x): x is { assignment: typeof x.assignment; chore: Chore } => x.chore !== undefined)
  );

  const assignedChoreIds = $derived(new Set(store.assignments.map((a) => a.choreId)));
  const unassignedChores = $derived(store.chores.filter((c) => !assignedChoreIds.has(c.id)));

  function displayName(chore: Chore): string {
    let name = chore.name.trim();
    if (chore.emoji && name.startsWith(chore.emoji)) {
      name = name.slice(chore.emoji.length).trim();
    }
    return name;
  }
</script>

<div class="panel">
  <div class="panel-header">Chores</div>

  {#if assigningChoreId}
    <div class="assign-banner">
      Click a room on the map to assign this chore.
      <button onclick={onCancelAssign}>Cancel</button>
    </div>
  {/if}

  {#if store.chores.length === 0}
    <div class="section">
      <div class="section-title">Import</div>
      {#if !showImportInput}
        <button class="primary-btn" onclick={() => { showImportInput = true; }}>
          Import from Donetick
        </button>
      {:else}
        <input
          type="password"
          placeholder="Donetick API token"
          bind:value={importToken}
          class="token-input"
        />
        <div class="row-btns">
          <button class="primary-btn" disabled={importStatus === "loading"} onclick={handleImport}>
            {importStatus === "loading" ? "Importing…" : "Import"}
          </button>
          <button onclick={() => { showImportInput = false; }}>Cancel</button>
        </div>
        {#if importStatus === "error"}
          <div class="error-msg">Import failed. Check your token.</div>
        {/if}
      {/if}
      {#if importStatus === "done"}
        <div class="success-msg">{importCount} chores imported.</div>
      {/if}
    </div>
  {/if}

  {#if houseChores.length > 0}
    <div class="section">
      <div class="section-title">🏠 Whole house</div>
      {#each houseChores as { assignment, chore }}
        <div class="chore-row">
          <span class="chore-emoji">{chore.emoji}</span>
          <span class="chore-name">{displayName(chore)}</span>
          <button class="done-btn" onclick={() => store.completeChore(chore.id)}>✓</button>
          <button class="icon-btn" onclick={() => store.deleteAssignment(assignment.id)}>✕</button>
        </div>
      {/each}
    </div>
  {/if}

  <div class="section chores-list">
    <div class="section-title">Unassigned ({unassignedChores.length})</div>
    {#each unassignedChores as chore (chore.id)}
      {@const pct = store.getProgress(chore)}
      {@const color = store.getColor(pct)}
      {#if editingId === chore.id}
        <div class="edit-form">
          <input class="edit-input" bind:value={editName} placeholder="Name"/>
          <input class="edit-input emoji-input" bind:value={editEmoji} placeholder="Emoji" maxlength="4"/>
          <label class="edit-label">Period (days)
            <input type="number" class="edit-input" bind:value={editPeriodDays} min="1"/>
          </label>
          <label class="edit-label">Next due
            <input type="date" class="edit-input" bind:value={editNextDue}/>
          </label>
          <div class="row-btns">
            <button class="primary-btn" onclick={handleUpdate}>Save</button>
            <button onclick={() => { editingId = null; }}>Cancel</button>
          </div>
        </div>
      {:else}
        {@const daysLeft = Math.round((new Date(chore.nextDueDate).getTime() - Date.now()) / 86400000)}
        <div class="chore-row" class:assigning={assigningChoreId === chore.id}>
          <svg width="22" height="22" viewBox="-11 -11 22 22" style="flex-shrink:0">
            <circle r="9" fill="none" stroke="#3a3a3a" stroke-width="3"/>
            <circle r="9" fill="none" stroke={color} stroke-width="3"
              stroke-dasharray="{pct * 56.5} 56.5" stroke-linecap="round"
              transform="rotate(-90 0 0)"/>
            <text text-anchor="middle" dominant-baseline="central" font-size="8">{chore.emoji}</text>
          </svg>
          <div class="chore-info">
            <span class="chore-name">{displayName(chore)}</span>
            <span class="chore-days" style="color:{color}">
              {daysLeft >= 0 ? `+${daysLeft}d` : `${daysLeft}d`}
            </span>
          </div>
          <div class="chore-actions">
            <button
              class="assign-btn"
              title="Assign to room"
              onclick={() => onAssignToRoom(chore.id)}
            >→</button>
            <button
              class="house-btn"
              title="Assign to whole house"
              onclick={() => store.createAssignment({ choreId: chore.id, roomId: null, position: null })}
            >🏠</button>
            <button class="icon-btn" title="Edit" onclick={() => startEdit(chore)}>✏️</button>
            <button class="icon-btn" title="Delete" onclick={() => store.deleteChore(chore.id)}>🗑️</button>
          </div>
        </div>
      {/if}
    {/each}
  </div>

  {#if showNewForm}
    <div class="section">
      <div class="section-title">New chore</div>
      <input class="edit-input" bind:value={newName} placeholder="Name (include emoji)"/>
      <input class="edit-input emoji-input" bind:value={newEmoji} placeholder="Emoji" maxlength="4"/>
      <label class="edit-label">Period (days)
        <input type="number" class="edit-input" bind:value={newPeriodDays} min="1"/>
      </label>
      <label class="edit-label">Next due
        <input type="date" class="edit-input" bind:value={newNextDue}/>
      </label>
      <div class="row-btns">
        <button class="primary-btn" onclick={handleCreate}>Add</button>
        <button onclick={() => { showNewForm = false; }}>Cancel</button>
      </div>
    </div>
  {:else}
    <button class="add-btn" onclick={() => { showNewForm = true; }}>＋ New chore</button>
  {/if}
</div>

<style>
  .panel {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 300px;
    background: #1e1e2e;
    border-left: 1px solid #333;
    overflow-y: auto;
    z-index: 10;
    display: flex;
    flex-direction: column;
    font-size: 12px;
    color: #ccc;
  }
  .panel-header {
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    color: #eee;
    border-bottom: 1px solid #333;
    background: #252535;
  }
  .assign-banner {
    background: #2a4a2a;
    padding: 8px 12px;
    color: #8f8;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .section {
    padding: 8px 12px;
    border-bottom: 1px solid #2a2a3a;
  }
  .section-title {
    font-size: 10px;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 6px;
    letter-spacing: 0.05em;
  }
  .chore-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 0;
  }
  .chore-row.assigning {
    background: #2a4a2a;
    border-radius: 4px;
    padding: 4px 4px;
  }
  .chore-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .chore-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 11px;
  }
  .chore-days {
    font-size: 10px;
  }
  .chore-emoji {
    font-size: 14px;
  }
  .chore-actions {
    display: flex;
    gap: 2px;
  }
  .chores-list {
    flex: 1;
  }
  button {
    padding: 3px 7px;
    border: none;
    border-radius: 3px;
    background: #3a3a5a;
    color: #ccc;
    cursor: pointer;
    font-size: 11px;
  }
  button:hover { background: #4a4a6a; }
  button:disabled { opacity: 0.5; cursor: default; }
  .primary-btn { background: #2a6; color: #fff; }
  .primary-btn:hover { background: #3b7; }
  .done-btn { color: #8f8; }
  .icon-btn { padding: 2px 4px; font-size: 10px; }
  .assign-btn { font-weight: bold; }
  .add-btn {
    margin: 8px 12px;
    display: block;
    width: calc(100% - 24px);
    padding: 6px;
    text-align: center;
    background: #2a2a4a;
    border: 1px dashed #444;
    color: #888;
    border-radius: 4px;
  }
  .add-btn:hover { background: #3a3a5a; color: #ccc; }
  .token-input, .edit-input {
    width: 100%;
    padding: 4px 6px;
    border: 1px solid #444;
    border-radius: 3px;
    background: #2a2a3a;
    color: #ccc;
    font-size: 11px;
    box-sizing: border-box;
    margin-bottom: 4px;
  }
  .emoji-input { width: 60px; }
  .edit-label {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: 4px;
    color: #888;
    font-size: 10px;
  }
  .row-btns { display: flex; gap: 6px; }
  .error-msg { color: #f44336; font-size: 11px; margin-top: 4px; }
  .success-msg { color: #4caf50; font-size: 11px; margin-top: 4px; }
</style>
