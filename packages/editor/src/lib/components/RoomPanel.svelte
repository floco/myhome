<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Room } from "@myhome/geometry";

  let {
    room,
    haAreas = [],
    readOnly = false,
    onupdate,
    onstartdrag,
    ondismiss,
  }: {
    room: Room;
    haAreas?: Array<{ area_id: string; name: string }>;
    readOnly?: boolean;
    onupdate: (patch: { label?: string; haAreaId?: string | null }) => void;
    onstartdrag?: (e: PointerEvent) => void;
    ondismiss?: () => void;
  } = $props();

  let labelDraft = $state("");

  $effect(() => {
    labelDraft = room.label;
  });

  function commitLabel(): void {
    const trimmed = labelDraft.trim();
    if (trimmed !== room.label) onupdate({ label: trimmed });
  }

  function handleAreaChange(e: Event): void {
    const val = (e.target as HTMLSelectElement).value;
    const next = val === "" ? null : val;
    if (next === room.haAreaId) return;
    const patch: { haAreaId: string | null; label?: string } = { haAreaId: next };
    if (next !== null && room.label.trim() === "") {
      const area = haAreas.find((a) => a.area_id === next);
      if (area) patch.label = area.name;
    }
    onupdate(patch);
  }
</script>

<aside class="room-panel">
  <div class="panel-header">
    {#if onstartdrag}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drag-handle" onpointerdown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
    {/if}
    <h2>{$_('floorPlan.roomPanel.title')}</h2>
    {#if ondismiss}
      <button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>
    {/if}
  </div>

  <label>
    <span>{$_('floorPlan.roomPanel.label')}</span>
    <input
      type="text"
      bind:value={labelDraft}
      disabled={readOnly}
      onblur={commitLabel}
      onkeydown={(e) => {
        if (e.key === "Enter") {
          commitLabel();
          (e.target as HTMLInputElement).blur();
        }
      }}
    />
  </label>

  <label>
    <span>{$_('floorPlan.roomPanel.haArea')}</span>
    <select value={room.haAreaId ?? ""} disabled={readOnly} onchange={handleAreaChange}>
      <option value="">{$_('floorPlan.roomPanel.none')}</option>
      {#each haAreas as area (area.area_id)}
        <option value={area.area_id}>{area.name}</option>
      {/each}
      {#if room.haAreaId && !haAreas.some((a) => a.area_id === room.haAreaId)}
        <option value={room.haAreaId}>{$_('floorPlan.roomPanel.unknownSuffix', { values: { id: room.haAreaId } })}</option>
      {/if}
    </select>
  </label>

  <p class="area-display">{room.areaM2} m²</p>
</aside>

<style>
  .room-panel {
    box-sizing: border-box;
    width: 200px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    overflow-y: auto;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .room-panel {
      width: 100%;
      height: 100%;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
    }
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  h2 {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
  }
  .drag-handle {
    cursor: grab;
    color: var(--text-muted);
    font-size: 14px;
    letter-spacing: 3px;
    opacity: 0.5;
    padding: 2px 0;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
    user-select: none;
  }
  .drag-handle:hover { opacity: 1; background: var(--surface-hover); }
  .drag-handle:active { cursor: grabbing; }
  .dismiss-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    flex-shrink: 0;
    padding: 2px 4px;
    border-radius: var(--radius-sm);
  }
  .dismiss-btn:hover { background: var(--surface-hover); color: var(--text); }
  label {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  span {
    font-size: 11px;
    color: var(--text-muted);
  }
  input,
  select {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 4px 6px;
    font-size: 12px;
    font-family: inherit;
  }
  input:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
  }
  .area-display {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
