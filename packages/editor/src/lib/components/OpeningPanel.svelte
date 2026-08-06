<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Opening } from "@myhome/geometry";

  interface HaEntity { entity_id: string; name: string }

  let {
    opening,
    areaIds = [],
    onupdate,
    onstartdrag,
    ondismiss,
  }: {
    opening: Opening;
    areaIds?: string[];
    onupdate: (patch: { haEntityId?: string | null; hasShutter?: boolean; shutterEntityId?: string | null }) => void;
    onstartdrag?: (e: PointerEvent) => void;
    ondismiss?: () => void;
  } = $props();

  let sensorEntities = $state<HaEntity[]>([]);
  let coverEntities = $state<HaEntity[]>([]);
  let controlInFlight = $state(false);

  async function fetchEntities(domain: string): Promise<HaEntity[]> {
    if (areaIds.length === 0) return [];
    const lists = await Promise.all(
      areaIds.map((areaId) =>
        fetch(`/api/ha/entities?area_id=${encodeURIComponent(areaId)}&domain=${domain}`)
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => [] as HaEntity[])
      )
    );
    const byId = new Map<string, HaEntity>();
    for (const list of lists as HaEntity[][]) for (const e of list) byId.set(e.entity_id, e);
    return [...byId.values()];
  }

  $effect(() => {
    fetchEntities("binary_sensor").then((list) => { sensorEntities = list; });
  });

  $effect(() => {
    if (opening.type !== "window") { coverEntities = []; return; }
    fetchEntities("cover").then((list) => { coverEntities = list; });
  });

  function handleSensorChange(e: Event): void {
    const val = (e.target as HTMLSelectElement).value;
    onupdate({ haEntityId: val === "" ? null : val });
  }

  function handleHasShutterChange(e: Event): void {
    const checked = (e.target as HTMLInputElement).checked;
    onupdate(checked ? { hasShutter: true } : { hasShutter: false, shutterEntityId: null });
  }

  function handleShutterEntityChange(e: Event): void {
    const val = (e.target as HTMLSelectElement).value;
    onupdate({ shutterEntityId: val === "" ? null : val });
  }

  async function sendCoverAction(action: "open" | "close" | "stop"): Promise<void> {
    if (!opening.shutterEntityId || controlInFlight) return;
    controlInFlight = true;
    try {
      await fetch(`/api/ha/cover/${encodeURIComponent(opening.shutterEntityId)}/${action}`, { method: "POST" });
    } finally {
      controlInFlight = false;
    }
  }
</script>

<aside class="opening-panel">
  <div class="panel-header">
    {#if onstartdrag}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drag-handle" onpointerdown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
    {/if}
    <h2>{$_('floorPlan.openingPanel.title')}</h2>
    {#if ondismiss}
      <button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>
    {/if}
  </div>

  <label>
    <span>{$_('floorPlan.openingPanel.sensor')}</span>
    <select value={opening.haEntityId ?? ""} onchange={handleSensorChange} disabled={areaIds.length === 0}>
      <option value="">{$_('floorPlan.openingPanel.none')}</option>
      {#each sensorEntities as entity (entity.entity_id)}
        <option value={entity.entity_id}>{entity.name}</option>
      {/each}
      {#if opening.haEntityId && !sensorEntities.some((e) => e.entity_id === opening.haEntityId)}
        <option value={opening.haEntityId}>{$_('floorPlan.openingPanel.unknownSuffix', { values: { id: opening.haEntityId } })}</option>
      {/if}
    </select>
    {#if areaIds.length === 0}
      <p class="hint">{$_('floorPlan.openingPanel.noArea')}</p>
    {/if}
  </label>

  {#if opening.type === "window"}
    <label class="checkbox-row">
      <input type="checkbox" checked={opening.hasShutter ?? false} onchange={handleHasShutterChange} />
      <span>{$_('floorPlan.openingPanel.hasShutter')}</span>
    </label>

    {#if opening.hasShutter}
      <label>
        <span>{$_('floorPlan.openingPanel.shutter')}</span>
        <select value={opening.shutterEntityId ?? ""} onchange={handleShutterEntityChange} disabled={areaIds.length === 0}>
          <option value="">{$_('floorPlan.openingPanel.none')}</option>
          {#each coverEntities as entity (entity.entity_id)}
            <option value={entity.entity_id}>{entity.name}</option>
          {/each}
          {#if opening.shutterEntityId && !coverEntities.some((e) => e.entity_id === opening.shutterEntityId)}
            <option value={opening.shutterEntityId}>{$_('floorPlan.openingPanel.unknownSuffix', { values: { id: opening.shutterEntityId } })}</option>
          {/if}
        </select>
      </label>

      {#if opening.shutterEntityId}
        <div class="shutter-controls">
          <button disabled={controlInFlight} onclick={() => sendCoverAction("open")}>{$_('floorPlan.openingPanel.open')}</button>
          <button disabled={controlInFlight} onclick={() => sendCoverAction("close")}>{$_('floorPlan.openingPanel.close')}</button>
          <button disabled={controlInFlight} onclick={() => sendCoverAction("stop")}>{$_('floorPlan.openingPanel.stop')}</button>
        </div>
      {/if}
    {/if}
  {/if}
</aside>

<style>
  .opening-panel {
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

  @media (max-width: 480px) {
    .opening-panel {
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
  .checkbox-row {
    flex-direction: row;
    align-items: center;
    gap: var(--space-2);
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
  input[type="checkbox"] { width: auto; }
  input:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
  }
  .hint {
    margin: 0;
    font-size: 10px;
    color: var(--text-faint);
  }
  .shutter-controls {
    display: flex;
    gap: var(--space-2);
  }
  .shutter-controls button {
    flex: 1;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 4px 6px;
    font-size: 11px;
    cursor: pointer;
  }
  .shutter-controls button:hover:not(:disabled) { background: var(--surface-hover); }
  .shutter-controls button:disabled { opacity: 0.5; cursor: default; }
</style>
