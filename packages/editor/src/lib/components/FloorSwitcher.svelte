<script lang="ts">
  import type { Floor } from "@myhome/geometry";

  let {
    floors,
    currentFloorId,
    onswitchfloor,
    onaddfloor,
    onrenamefloor,
    onremovefloor,
    compact = false,
  }: {
    floors: Floor[];
    currentFloorId: string;
    onswitchfloor: (id: string) => void;
    onaddfloor?: (name: string) => void;
    onrenamefloor?: (id: string, name: string) => void;
    onremovefloor?: (id: string) => void;
    compact?: boolean;
  } = $props();

  const ALL_FLOOR_ID = "__all__";

  let editingId = $state<string | null>(null);
  let editingName = $state("");
  let compactOpen = $state(false);

  const currentFloorName = $derived(
    currentFloorId === ALL_FLOOR_ID
      ? "All"
      : (floors.find((f) => f.id === currentFloorId)?.name ?? "—")
  );

  function handleFloorClick(floor: Floor, event: MouseEvent): void {
    if (floor.id !== currentFloorId) {
      onswitchfloor(floor.id);
      return;
    }
    if (onrenamefloor && (event as MouseEvent & { detail: number }).detail === 2) {
      editingId = floor.id;
      editingName = floor.name;
    }
  }

  function commitRename(): void {
    if (!editingId) return;
    const trimmed = editingName.trim();
    if (trimmed) onrenamefloor?.(editingId, trimmed);
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
    onaddfloor?.(name);
  }

  function selectCompact(id: string): void {
    onswitchfloor(id);
    compactOpen = false;
  }
</script>

{#if compact}
  <div class="compact-switcher">
    <button
      class="compact-btn"
      onclick={() => { compactOpen = !compactOpen; }}
      title="Switch floor"
    >
      <span class="compact-label">{currentFloorName}</span>
      <span class="compact-chevron">{compactOpen ? "▴" : "▾"}</span>
    </button>

    {#if compactOpen}
      <div class="compact-popover">
        <button
          class="compact-floor-item"
          class:active={currentFloorId === ALL_FLOOR_ID}
          onclick={() => selectCompact(ALL_FLOOR_ID)}
        >🏠 All</button>
        {#each floors as floor (floor.id)}
          <button
            class="compact-floor-item"
            class:active={floor.id === currentFloorId}
            onclick={() => selectCompact(floor.id)}
          >{floor.name}</button>
        {/each}
        {#if onaddfloor}
          <hr class="compact-sep" />
          <button class="compact-floor-item add" onclick={() => { handleAddFloor(); compactOpen = false; }}>＋ Add floor</button>
        {/if}
      </div>
    {/if}
  </div>
{:else}
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
        {#if onremovefloor && floors.length > 1}
          <button
            class="remove-btn"
            onclick={() => onremovefloor(floor.id)}
            title="Delete floor"
            aria-label="Delete {floor.name}"
          >×</button>
        {/if}
      </div>
    {/each}
    {#if onaddfloor}
      <button class="add-btn" onclick={handleAddFloor}>+ Floor</button>
    {/if}
  </div>
{/if}

<style>
  /* ── Compact variant ── */
  .compact-switcher { position: relative; }

  .compact-btn {
    display: flex; align-items: center; gap: 4px;
    width: 100%; padding: 4px 6px;
    border: none; background: none; border-radius: var(--radius-sm);
    cursor: pointer; color: var(--text); font-size: 11px; font-weight: 500;
    white-space: nowrap; justify-content: center;
  }
  .compact-btn:hover { background: var(--surface-hover); }
  .compact-label { max-width: 70px; overflow: hidden; text-overflow: ellipsis; }
  .compact-chevron { font-size: 9px; color: var(--text-muted); flex-shrink: 0; }

  .compact-popover {
    position: absolute; right: calc(100% + 6px); top: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 100; padding: 4px; min-width: 130px;
  }

  .compact-floor-item {
    display: block; width: 100%; padding: 6px 10px;
    border: none; background: none; border-radius: var(--radius-sm);
    cursor: pointer; color: var(--text); font-size: 12px; text-align: left;
  }
  .compact-floor-item:hover { background: var(--surface-hover); }
  .compact-floor-item.active { background: var(--accent); color: var(--accent-contrast); }
  .compact-floor-item.add { color: var(--text-muted); }
  .compact-sep { border: none; border-top: 1px solid var(--border); margin: 4px 0; }

  /* ── Full (default) variant ── */
  .floor-switcher {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .floor-btn {
    display: flex;
    align-items: center;
    border-radius: var(--radius-sm);
    background: var(--surface-alt);
    overflow: hidden;
  }

  .floor-btn.active {
    background: var(--surface-hover);
    outline: 1px solid var(--accent);
  }

  .floor-label {
    padding: 3px 8px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
  }

  .floor-btn.active .floor-label {
    color: var(--text);
  }

  .remove-btn {
    padding: 3px 5px;
    border: none;
    border-left: 1px solid var(--border);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    font-size: 11px;
    line-height: 1;
  }

  .remove-btn:hover {
    color: var(--danger);
    background: var(--surface-hover);
  }

  .rename-input {
    width: 90px;
    padding: 2px 6px;
    background: var(--surface-alt);
    border: 1px solid var(--accent);
    border-radius: var(--radius-sm);
    color: var(--text);
    font-size: 12px;
  }

  .add-btn {
    padding: 3px 8px;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--surface-alt);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
  }

  .add-btn:hover {
    background: var(--surface-hover);
    color: var(--text);
  }
</style>
