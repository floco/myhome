<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    onback: () => void;
    floorStore: { floors: Array<{ id: string; name: string; rooms: Array<{ id: string; label: string }> }> };
  }

  let { store, onback, floorStore }: Props = $props();

  function getRoomName(roomId: string): string {
    for (const floor of floorStore.floors) {
      const room = floor.rooms.find((r) => r.id === roomId);
      if (room) return room.label || `Room (${floor.name})`;
    }
    return "Unknown room";
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
    newName = ""; newEmoji = "📋"; newPeriodDays = 30;
    newNextDue = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  }

  let editingId = $state<string | null>(null);
  let editName = $state(""); let editEmoji = $state(""); let editPeriodDays = $state(30); let editNextDue = $state("");

  function startEdit(chore: Chore): void {
    editingId = chore.id; editName = chore.name; editEmoji = chore.emoji;
    editPeriodDays = chore.periodDays; editNextDue = chore.nextDueDate.slice(0, 10);
  }

  async function handleUpdate(): Promise<void> {
    if (!editingId) return;
    await store.updateChore(editingId, {
      name: editName.trim(), emoji: editEmoji.trim() || "📋",
      periodDays: editPeriodDays, nextDueDate: new Date(editNextDue).toISOString(),
    });
    editingId = null;
  }

  function assignmentsForChore(choreId: string) {
    return store.assignments.filter((a) => a.choreId === choreId);
  }

  function formatDate(iso: string): string {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await store.importFromDonetick(importToken.trim());
      importStatus = "done"; importToken = ""; showImportInput = false;
    } catch { importStatus = "error"; }
  }
</script>

<div class="page">
  <header class="page-header">
    <button class="back-btn" onclick={onback}>← Floor Plan</button>
    <h1>Chore Management</h1>
    {#if !showImportInput}
      <button onclick={() => { showImportInput = true; }}>Import from Donetick</button>
    {:else}
      <input type="password" placeholder="API token" bind:value={importToken} class="token-input"/>
      <button disabled={importStatus === "loading"} onclick={handleImport}>
        {importStatus === "loading" ? "Importing…" : "Import"}
      </button>
      <button onclick={() => { showImportInput = false; }}>Cancel</button>
      {#if importStatus === "error"}<span class="error-msg">Failed</span>{/if}
      {#if importStatus === "done"}<span class="success-msg">{importCount} imported</span>{/if}
    {/if}
  </header>

  <div class="chore-list">
    {#each store.chores as chore (chore.id)}
      <div class="chore-card">
        {#if editingId === chore.id}
          <div class="edit-form">
            <input bind:value={editName} placeholder="Name"/>
            <input bind:value={editEmoji} placeholder="Emoji" maxlength="4" style="width:60px"/>
            <label>Period (days) <input type="number" bind:value={editPeriodDays} min="1"/></label>
            <label>Default due <input type="date" bind:value={editNextDue}/></label>
            <div class="row-btns">
              <button class="primary-btn" onclick={handleUpdate}>Save</button>
              <button onclick={() => { editingId = null; }}>Cancel</button>
            </div>
          </div>
        {:else}
          <div class="chore-header">
            <span class="chore-emoji">{chore.emoji}</span>
            <span class="chore-name">{chore.name}</span>
            <span class="chore-period">{chore.periodDays}d</span>
            <button onclick={() => store.completeChore(chore.id)}>✓ Mark all done</button>
            <button onclick={() => startEdit(chore)}>✏️</button>
            <button onclick={() => store.deleteChore(chore.id)}>🗑️</button>
          </div>
          {@const instances = assignmentsForChore(chore.id)}
          {#if instances.length > 0}
            <div class="instances">
              {#each instances as a (a.id)}
                <div class="instance-row">
                  <span class="instance-where">
                    {a.roomId ? getRoomName(a.roomId) : "🏠 Whole house"}
                  </span>
                  <span class="instance-due">Due: {formatDate(a.nextDueDate)}</span>
                  <button onclick={() => store.completeAssignment(a.id)}>✓</button>
                  <button onclick={() => store.deleteAssignment(a.id)}>✕</button>
                </div>
              {/each}
            </div>
          {:else}
            <div class="no-instances">Not assigned to any room</div>
          {/if}
        {/if}
      </div>
    {/each}

    {#if showNewForm}
      <div class="chore-card new-form">
        <input bind:value={newName} placeholder="Name (include emoji)"/>
        <input bind:value={newEmoji} placeholder="Emoji" maxlength="4" style="width:60px"/>
        <label>Period (days) <input type="number" bind:value={newPeriodDays} min="1"/></label>
        <label>Default due <input type="date" bind:value={newNextDue}/></label>
        <div class="row-btns">
          <button class="primary-btn" onclick={handleCreate}>Add</button>
          <button onclick={() => { showNewForm = false; }}>Cancel</button>
        </div>
      </div>
    {:else}
      <button class="add-btn" onclick={() => { showNewForm = true; }}>＋ New chore</button>
    {/if}
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100vh; background: #1a1a2e; color: #ccc; font-family: sans-serif; }
  .page-header { display: flex; align-items: center; gap: 12px; padding: 8px 16px; background: #252535; border-bottom: 1px solid #333; flex-shrink: 0; }
  .page-header h1 { font-size: 16px; margin: 0; flex: 1; }
  .back-btn { padding: 4px 10px; border: none; border-radius: 4px; background: #3a3a5a; color: #ccc; cursor: pointer; font-size: 12px; }
  .chore-list { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .chore-card { background: #252535; border: 1px solid #333; border-radius: 6px; padding: 12px; }
  .chore-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .chore-emoji { font-size: 18px; }
  .chore-name { flex: 1; font-weight: 600; color: #eee; }
  .chore-period { font-size: 11px; color: #666; margin-right: 8px; }
  .instances { display: flex; flex-direction: column; gap: 4px; padding-left: 12px; border-left: 2px solid #333; }
  .instance-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
  .instance-where { flex: 1; color: #aaa; }
  .instance-due { color: #666; font-size: 11px; }
  .no-instances { font-size: 11px; color: #555; padding-left: 12px; font-style: italic; }
  button { padding: 3px 8px; border: none; border-radius: 3px; background: #3a3a5a; color: #ccc; cursor: pointer; font-size: 11px; }
  button:hover { background: #4a4a6a; }
  button:disabled { opacity: 0.5; cursor: default; }
  .primary-btn { background: #2a6; color: #fff; }
  .primary-btn:hover { background: #3b7; }
  .add-btn { display: block; width: 100%; padding: 10px; text-align: center; background: #2a2a4a; border: 1px dashed #444; color: #888; border-radius: 4px; cursor: pointer; }
  .add-btn:hover { background: #3a3a5a; color: #ccc; }
  input { padding: 4px 6px; border: 1px solid #444; border-radius: 3px; background: #2a2a3a; color: #ccc; font-size: 12px; margin-bottom: 4px; }
  input[type="number"], input[type="date"] { width: 120px; }
  label { display: flex; flex-direction: column; gap: 2px; font-size: 11px; color: #888; margin-bottom: 4px; }
  .row-btns { display: flex; gap: 8px; margin-top: 4px; }
  .token-input { width: 220px; }
  .error-msg { color: #f44336; font-size: 11px; }
  .success-msg { color: #4caf50; font-size: 11px; }
</style>
