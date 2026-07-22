<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Room } from "@myhome/geometry";

  let {
    room,
    haAreas = [],
    onupdate,
  }: {
    room: Room;
    haAreas?: Array<{ area_id: string; name: string }>;
    onupdate: (patch: { label?: string; haAreaId?: string | null }) => void;
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
    if (next !== room.haAreaId) onupdate({ haAreaId: next });
  }
</script>

<aside class="room-panel">
  <h2>{$_('floorPlan.roomPanel.title')}</h2>

  <label>
    <span>{$_('floorPlan.roomPanel.label')}</span>
    <input
      type="text"
      bind:value={labelDraft}
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
    <select value={room.haAreaId ?? ""} onchange={handleAreaChange}>
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
    position: absolute;
    right: 120px;
    top: 50%;
    transform: translateY(-50%);
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
    z-index: 20;
  }
  h2 {
    margin: 0;
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
  }
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
