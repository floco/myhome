<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Floor } from "@myhome/geometry";

  let {
    floors,
    currentFloorId,
    onswitchfloor,
    onaddfloor,
    onrenamefloor,
    onremovefloor,
    compact = false,
    showAllOption = true,
    variant = 'toolbar',
  }: {
    floors: Floor[];
    currentFloorId: string;
    onswitchfloor: (id: string) => void;
    onaddfloor?: (name: string) => void;
    onrenamefloor?: (id: string, name: string) => void;
    onremovefloor?: (id: string) => void;
    compact?: boolean;
    /** Whether the "All floors" (house-wide) entry is offered. Off for
     *  contexts like the home dashboard widget, which always shows a
     *  single floor and has no whole-house mode. */
    showAllOption?: boolean;
    /** Compact-mode trigger look: 'toolbar' (default) is borderless, for the
     *  floor-plan editor's floating toolbar; 'pill' is a bordered box,
     *  matching LayersDropdown's standalone-widget look. */
    variant?: 'toolbar' | 'pill';
  } = $props();

  const ALL_FLOOR_ID = "__all__";

  let editingId = $state<string | null>(null);
  let editingName = $state("");
  let compactOpen = $state(false);
  let compactWrapper = $state<HTMLElement | null>(null);
  let compactTrigger = $state<HTMLButtonElement | null>(null);
  let compactPanel = $state<HTMLElement | null>(null);
  let compactTop = $state<number | null>(null);
  let compactBottom = $state<number | null>(null);
  let compactLeft = $state<number | null>(null);
  let compactRight = $state<number | null>(null);

  // Teleport the panel to <body> so position:fixed isn't clipped by an
  // ancestor with overflow set (e.g. the mobile floating-toolbar's
  // overflow-x:auto) -- same mechanism as EmojiPicker.svelte's portal action.
  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  function toggleCompact(): void {
    if (!compactOpen && compactTrigger) {
      const rect = compactTrigger.getBoundingClientRect();
      if (rect.top > window.innerHeight / 2) {
        compactBottom = window.innerHeight - rect.top + 4;
        compactTop = null;
      } else {
        compactTop = rect.bottom + 4;
        compactBottom = null;
      }
      // Anchor by the panel's left edge (clamped into the viewport) rather
      // than right-aligning to the button -- the compact switcher can sit
      // at the far left of the mobile toolbar, where a right-anchored
      // panel would run off the left edge of the screen.
      compactLeft = Math.max(4, Math.min(rect.left, window.innerWidth - 140));
      compactRight = null;
    }
    compactOpen = !compactOpen;
  }

  const currentFloorName = $derived(
    currentFloorId === ALL_FLOOR_ID
      ? $_('floorPlan.switcher.all')
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
    const keys = ["groundFloor", "firstFloor", "secondFloor", "thirdFloor", "basement"];
    const name = keys[n - 1] ? $_(`floorPlan.switcher.${keys[n - 1]}`) : $_('floorPlan.switcher.defaultFloorName', { values: { n } });
    onaddfloor?.(name);
  }

  function selectCompact(id: string): void {
    onswitchfloor(id);
    compactOpen = false;
  }

  function handleClickOutside(e: MouseEvent): void {
    const target = e.target as Node;
    if (compactWrapper?.contains(target) || compactPanel?.contains(target)) return;
    compactOpen = false;
  }
</script>

<svelte:window onclick={handleClickOutside} />

{#if compact}
  <div class="compact-switcher" bind:this={compactWrapper}>
    <button
      class="compact-btn"
      class:pill={variant === 'pill'}
      bind:this={compactTrigger}
      onclick={toggleCompact}
      title={$_('floorPlan.switcher.switchFloor')}
    >
      <span class="compact-icon" aria-hidden="true">🏢</span>
      <span class="compact-label">{currentFloorName}</span>
      <span class="compact-chevron">{compactOpen ? "▴" : "▾"}</span>
    </button>

    {#if compactOpen}
      <div
        class="compact-popover"
        style="{compactTop !== null ? `top:${compactTop}px;` : ''}{compactBottom !== null ? `bottom:${compactBottom}px;` : ''}{compactLeft !== null ? `left:${compactLeft}px;` : ''}{compactRight !== null ? `right:${compactRight}px;` : ''}"
        bind:this={compactPanel}
        use:portal
      >
        {#if showAllOption}
          <button
            class="compact-floor-item"
            class:active={currentFloorId === ALL_FLOOR_ID}
            title={$_('floorPlan.switcher.houseWide')}
            onclick={() => selectCompact(ALL_FLOOR_ID)}
          >🏠 {$_('floorPlan.switcher.all')}</button>
        {/if}
        {#each floors as floor (floor.id)}
          <button
            class="compact-floor-item"
            class:active={floor.id === currentFloorId}
            onclick={() => selectCompact(floor.id)}
          >{floor.name}</button>
        {/each}
        {#if onaddfloor}
          <hr class="compact-sep" />
          <button class="compact-floor-item add" onclick={() => { handleAddFloor(); compactOpen = false; }}>＋ {$_('floorPlan.switcher.addFloor')}</button>
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
        title={$_('floorPlan.switcher.houseWide')}
      >🏠 {$_('floorPlan.switcher.all')}</button>
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
            title={floor.id === currentFloorId ? $_('floorPlan.switcher.doubleClickToRename') : $_('floorPlan.switcher.switchToThisFloor')}
          >
            {floor.name}
          </button>
        {/if}
        {#if onremovefloor && floors.length > 1}
          <button
            class="remove-btn"
            onclick={() => onremovefloor(floor.id)}
            title={$_('floorPlan.switcher.deleteFloor')}
            aria-label={$_('floorPlan.switcher.deleteFloorAriaLabel', { values: { name: floor.name } })}
          >×</button>
        {/if}
      </div>
    {/each}
    {#if onaddfloor}
      <button class="add-btn" onclick={handleAddFloor}>+ {$_('floorPlan.switcher.floor')}</button>
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
  .compact-icon { display: none; font-size: 13px; line-height: 1; }
  .compact-label { max-width: 70px; overflow: hidden; text-overflow: ellipsis; }
  .compact-chevron { font-size: 9px; color: var(--text-muted); flex-shrink: 0; }

  /* 'pill' variant mirrors LayersDropdown's standalone-widget look (bordered
     box) for contexts like the home dashboard, as opposed to the borderless
     look that blends into the floor-plan editor's floating toolbar. */
  .compact-btn.pill {
    padding: 3px 10px; height: 26px; box-sizing: border-box;
    border: 1px solid var(--border); background: var(--surface-alt);
    color: var(--text-muted);
  }
  .compact-btn.pill:hover { background: var(--surface-hover); }

  @media (max-width: 480px) { /* --bp-mobile */
    .compact-switcher { flex: 1 1 0; max-width: 44px; aspect-ratio: 1 / 1; }
    .compact-btn { width: 100%; height: 100%; padding: 0; }
    .compact-icon { display: inline-block; font-size: 22px; }
    .compact-label { display: none; }
    .compact-chevron { display: none; }
  }

  .compact-popover {
    position: fixed;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 9999; padding: 4px; min-width: 130px;
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
