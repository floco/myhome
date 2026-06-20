<script lang="ts">
  import type { Floor } from "@myhome/geometry";

  let {
    floors,
    currentFloorId,
    onswitchfloor,
    onaddfloor,
    onrenamefloor,
    onremovefloor,
  }: {
    floors: Floor[];
    currentFloorId: string;
    onswitchfloor: (id: string) => void;
    onaddfloor: (name: string) => void;
    onrenamefloor: (id: string, name: string) => void;
    onremovefloor: (id: string) => void;
  } = $props();

  const ALL_FLOOR_ID = "__all__";

  let editingId = $state<string | null>(null);
  let editingName = $state("");

  function handleFloorClick(floor: Floor, event: MouseEvent): void {
    if (floor.id !== currentFloorId) {
      onswitchfloor(floor.id);
      return;
    }
    if ((event as MouseEvent & { detail: number }).detail === 2) {
      editingId = floor.id;
      editingName = floor.name;
    }
  }

  function commitRename(): void {
    if (!editingId) return;
    const trimmed = editingName.trim();
    if (trimmed) onrenamefloor(editingId, trimmed);
    editingId = null;
  }

  function handleRenameKey(event: KeyboardEvent): void {
    if (event.key === "Enter") commitRename();
    if (event.key === "Escape") editingId = null;
  }

  function handleAddFloor(): void {
    const n = floors.length + 1;
    const names = ["Ground Floor", "First Floor", "Second Floor", "Third Floor", "Basement"];
    const name = names[n - 1] ?? `Floor ${n}`;
    onaddfloor(name);
  }
</script>

<div class="floor-switcher">
  <div class="floor-btn all-btn" class:active={currentFloorId === ALL_FLOOR_ID}>
    <button
      class="floor-label"
      onclick={() => onswitchfloor(ALL_FLOOR_ID)}
      title="House-wide assignments — drag chores here"
    >🏠 All</button>
  </div>
  {#each floors as floor (floor.id)}
    <div class="floor-btn" class:active={floor.id === currentFloorId}>
      {#if editingId === floor.id}
        <input
          class="rename-input"
          bind:value={editingName}
          onblur={commitRename}
          onkeydown={handleRenameKey}
          autofocus
        />
      {:else}
        <button
          class="floor-label"
          onclick={(e) => handleFloorClick(floor, e)}
          title={floor.id === currentFloorId ? "Double-click to rename" : "Switch to this floor"}
        >
          {floor.name}
        </button>
      {/if}
      {#if floors.length > 1}
        <button
          class="remove-btn"
          onclick={() => onremovefloor(floor.id)}
          title="Delete floor"
          aria-label="Delete {floor.name}"
        >×</button>
      {/if}
    </div>
  {/each}
  <button class="add-btn" onclick={handleAddFloor}>+ Floor</button>
</div>

<style>
  .floor-switcher {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .floor-btn {
    display: flex;
    align-items: center;
    border-radius: 4px;
    background: #444;
    overflow: hidden;
  }

  .floor-btn.active {
    background: #555;
    outline: 1px solid #5af;
  }

  .floor-label {
    padding: 3px 8px;
    border: none;
    background: transparent;
    color: #ccc;
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
  }

  .floor-btn.active .floor-label {
    color: #eee;
  }

  .remove-btn {
    padding: 3px 5px;
    border: none;
    border-left: 1px solid #333;
    background: transparent;
    color: #888;
    cursor: pointer;
    font-size: 11px;
    line-height: 1;
  }

  .remove-btn:hover {
    color: #f66;
    background: rgba(255, 0, 0, 0.1);
  }

  .rename-input {
    width: 90px;
    padding: 2px 6px;
    background: #2a2a2a;
    border: 1px solid #5af;
    border-radius: 2px;
    color: #eee;
    font-size: 12px;
  }

  .add-btn {
    padding: 3px 8px;
    border: none;
    border-radius: 4px;
    background: #383838;
    color: #aaa;
    cursor: pointer;
    font-size: 12px;
  }

  .add-btn:hover {
    background: #444;
    color: #ccc;
  }

  .all-btn .floor-label { color: #aaf; }
  .all-btn.active .floor-label { color: #ccf; }
</style>
