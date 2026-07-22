<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createLocationsStore, Location, LocationCriterion, Weight } from "../locationsStore.svelte";
  import { ratingFor, bestScoreForCriterion } from "../locationsStore.svelte";
  import LocationRatingPopup from "./LocationRatingPopup.svelte";
  import LocationModal from "./LocationModal.svelte";
  import LocationCriterionModal from "./LocationCriterionModal.svelte";
  import StarRating from "./ui/StarRating.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;
  interface Props { store: LocationsStore; }
  let { store }: Props = $props();

  function weightLabel(w: Weight): string {
    if (w === "low") return $_('locations.criterionModal.low');
    if (w === "high") return $_('locations.criterionModal.high');
    return $_('locations.matrix.weightMed');
  }

  let mode = $state<"view" | "edit">("view");

  let confirmDeleteCriterionId = $state<string | null>(null);
  let confirmDeleteLocationId = $state<string | null>(null);

  let showLocationModal = $state<Location | "new" | null>(null);
  let showCriterionModal = $state<LocationCriterion | "new" | null>(null);

  let openCell = $state<{ locationId: string; criterionId: string; anchorX: number; anchorY: number } | null>(null);

  async function moveCriterion(id: string, dir: -1 | 1): Promise<void> {
    const ids = store.criteria.map((c) => c.id);
    const idx = ids.indexOf(id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= ids.length) return;
    [ids[idx], ids[swapWith]] = [ids[swapWith], ids[idx]];
    await store.reorderCriteria(ids);
  }

  async function moveLocation(id: string, dir: -1 | 1): Promise<void> {
    const ids = store.locations.map((l) => l.id);
    const idx = ids.indexOf(id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= ids.length) return;
    [ids[idx], ids[swapWith]] = [ids[swapWith], ids[idx]];
    await store.reorderLocations(ids);
  }

  async function handleSaveLocation(data: { name: string; emoji: string }): Promise<void> {
    if (showLocationModal === "new") {
      await store.createLocation(data);
    } else if (showLocationModal) {
      await store.updateLocation(showLocationModal.id, data);
    }
  }

  async function handleSaveCriterion(data: { name: string; description: string; weight: Weight }): Promise<void> {
    if (showCriterionModal === "new") {
      await store.createCriterion(data);
    } else if (showCriterionModal) {
      await store.updateCriterion(showCriterionModal.id, data);
    }
  }

  // Popup is ~240px wide and its height varies with note length but rarely
  // exceeds ~220px -- clamp both axes so it can't render (and be unclickable)
  // past the viewport edge for cells near the right edge or bottom of the table.
  const POPUP_WIDTH = 240;
  const POPUP_HEIGHT_ESTIMATE = 220;

  function openRatingPopup(locationId: string, criterionId: string, e: MouseEvent): void {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const anchorX = Math.max(4, Math.min(rect.left, window.innerWidth - POPUP_WIDTH - 4));
    const anchorY = rect.bottom + POPUP_HEIGHT_ESTIMATE > window.innerHeight
      ? Math.max(4, rect.top - POPUP_HEIGHT_ESTIMATE)
      : rect.bottom;
    openCell = { locationId, criterionId, anchorX, anchorY };
  }

  async function handleSaveRating(score: number | null, note: string): Promise<void> {
    if (!openCell) return;
    if (score === null && note.trim() === "") {
      await store.clearRating(openCell.locationId, openCell.criterionId);
    } else {
      await store.setRating(openCell.locationId, openCell.criterionId, score, note);
    }
    openCell = null;
  }
</script>

<div class="mode-bar">
  <div class="mode-toggle">
    <button type="button" class="mode-btn" class:active={mode === "view"} onclick={() => { mode = "view"; }}>👁 {$_('locations.matrix.view')}</button>
    <button type="button" class="mode-btn" class:active={mode === "edit"} onclick={() => { mode = "edit"; }}>✏️ {$_('common.edit')}</button>
  </div>
</div>

<div class="matrix-wrapper">
  <table class="matrix">
    <thead>
      <tr>
        <th class="corner">
          {$_('locations.matrix.criteria')}
          {#if mode === "edit"}
            <button class="add-btn" onclick={() => { showCriterionModal = "new"; }} title={$_('locations.criterionModal.addCriterion')}>＋</button>
          {/if}
        </th>
        {#each store.locations as loc (loc.id)}
          <th class="location-header">
            {#if confirmDeleteLocationId === loc.id}
              <div class="header-content">
                <span class="confirm-text">{$_('locations.matrix.deleteLocationConfirm', { values: { name: loc.name } })}</span>
                <div class="header-actions">
                  <button class="icon-btn" onclick={() => { store.deleteLocation(loc.id); confirmDeleteLocationId = null; }} title={$_('locations.matrix.confirmDelete')}>✓</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteLocationId = null; }} title={$_('common.cancel')}>✕</button>
                </div>
              </div>
            {:else}
              <div class="header-content">
                <span class="loc-emoji">{loc.emoji}</span>
                <span class="loc-name">{loc.name}</span>
                {#if mode === "edit"}
                  <div class="header-actions">
                    <button class="icon-btn" onclick={() => moveLocation(loc.id, -1)} title={$_('locations.matrix.moveLeft')}>◀</button>
                    <button class="icon-btn" onclick={() => moveLocation(loc.id, 1)} title={$_('locations.matrix.moveRight')}>▶</button>
                    <button class="icon-btn" onclick={() => { showLocationModal = loc; }} title={$_('common.edit')}>✏️</button>
                    <button class="icon-btn" onclick={() => { confirmDeleteLocationId = loc.id; }} title={$_('common.delete')}>🗑</button>
                  </div>
                {/if}
              </div>
            {/if}
          </th>
        {/each}
        {#if mode === "edit"}
          <th class="add-header">
            <button class="add-btn" onclick={() => { showLocationModal = "new"; }} title={$_('locations.matrix.addLocationTitle')}>＋</button>
          </th>
        {/if}
      </tr>
    </thead>
    <tbody>
      {#each store.criteria as criterion (criterion.id)}
        {@const best = bestScoreForCriterion(store.locations, store.ratings, criterion.id)}
        <tr>
          <td class="criterion-cell">
            {#if confirmDeleteCriterionId === criterion.id}
              <div class="criterion-content">
                <span class="confirm-text">{$_('locations.matrix.deleteCriterionConfirm', { values: { name: criterion.name } })}</span>
                <div class="row-actions">
                  <button class="icon-btn" onclick={() => { store.deleteCriterion(criterion.id); confirmDeleteCriterionId = null; }} title={$_('locations.matrix.confirmDelete')}>✓</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteCriterionId = null; }} title={$_('common.cancel')}>✕</button>
                </div>
              </div>
            {:else}
              <div class="criterion-content">
                <div class="criterion-title-row">
                  <span class="criterion-name">{criterion.name}</span>
                  <span class="weight-tag weight-{criterion.weight}">{weightLabel(criterion.weight)}</span>
                </div>
                {#if criterion.description}<p class="criterion-desc">{criterion.description}</p>{/if}
                {#if mode === "edit"}
                  <div class="row-actions">
                    <button class="icon-btn" onclick={() => moveCriterion(criterion.id, -1)} title={$_('locations.matrix.moveUp')}>▲</button>
                    <button class="icon-btn" onclick={() => moveCriterion(criterion.id, 1)} title={$_('locations.matrix.moveDown')}>▼</button>
                    <button class="icon-btn" onclick={() => { showCriterionModal = criterion; }} title={$_('common.edit')}>✏️</button>
                    <button class="icon-btn" onclick={() => { confirmDeleteCriterionId = criterion.id; }} title={$_('common.delete')}>🗑</button>
                  </div>
                {/if}
              </div>
            {/if}
          </td>
          {#each store.locations as loc (loc.id)}
            {@const rating = ratingFor(store.ratings, loc.id, criterion.id)}
            {@const isBest = rating?.score != null && best !== null && rating.score === best}
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
            <td
              class="rating-cell"
              class:best={isBest}
              role="button"
              tabindex="0"
              onclick={(e) => openRatingPopup(loc.id, criterion.id, e)}
            >
              {#if rating?.score != null}
                <StarRating score={rating.score} size="sm" />
                {#if rating.note}<span class="note-preview">{rating.note}</span>{/if}
              {:else}
                <span class="score-empty">—</span>
              {/if}
            </td>
          {/each}
          {#if mode === "edit"}
            <td class="add-criterion-filler"></td>
          {/if}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

{#if showLocationModal}
  <LocationModal
    location={showLocationModal === "new" ? null : showLocationModal}
    onsave={handleSaveLocation}
    onclose={() => { showLocationModal = null; }}
  />
{/if}

{#if showCriterionModal}
  <LocationCriterionModal
    criterion={showCriterionModal === "new" ? null : showCriterionModal}
    onsave={handleSaveCriterion}
    onclose={() => { showCriterionModal = null; }}
  />
{/if}

{#if openCell}
  {@const cellLocation = store.locations.find((l) => l.id === openCell!.locationId)}
  {@const cellCriterion = store.criteria.find((c) => c.id === openCell!.criterionId)}
  {#if cellLocation && cellCriterion}
    <LocationRatingPopup
      location={cellLocation}
      criterion={cellCriterion}
      rating={ratingFor(store.ratings, openCell.locationId, openCell.criterionId)}
      anchorX={openCell.anchorX}
      anchorY={openCell.anchorY}
      onsave={handleSaveRating}
      onclose={() => { openCell = null; }}
    />
  {/if}
{/if}

<style>
  .mode-bar { display: flex; justify-content: flex-end; padding: 8px 10px 0; }
  .mode-toggle { display: flex; gap: 2px; background: var(--surface-alt); border-radius: var(--radius-pill); padding: 2px; }
  .mode-btn {
    border: none; background: none; color: var(--text-muted); border-radius: var(--radius-pill);
    padding: 4px 12px; cursor: pointer; font-size: 11px; font-weight: 600;
  }
  .mode-btn.active { background: var(--accent); color: var(--accent-contrast); }

  .matrix-wrapper { overflow-x: auto; }
  .matrix { width: 100%; border-collapse: collapse; font-size: 12px; }
  .matrix th, .matrix td { border-bottom: 1px solid var(--border); padding: 8px 10px; vertical-align: top; text-align: left; }
  .corner { min-width: 220px; color: var(--text-faint); font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.05em; }
  .location-header, .add-header { min-width: 160px; }
  .header-content { display: flex; flex-direction: column; gap: 4px; }
  .loc-emoji { font-size: 18px; }
  .loc-name { font-weight: 600; color: var(--text); }
  .header-actions, .row-actions { display: flex; gap: 4px; }
  .icon-btn { border: none; background: var(--surface-alt); color: var(--text-muted); border-radius: var(--radius-sm); padding: 2px 6px; cursor: pointer; font-size: 11px; }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .add-btn { border: none; background: var(--accent); color: var(--accent-contrast); border-radius: var(--radius-sm); padding: 4px 10px; cursor: pointer; font-size: 13px; flex-shrink: 0; }
  .confirm-text { font-size: 11px; color: var(--danger); }

  .criterion-cell { min-width: 240px; }
  .criterion-title-row { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
  .criterion-name { font-weight: 600; color: var(--text); }
  .criterion-desc { margin: 2px 0 6px; color: var(--text-muted); font-size: 11px; }
  .weight-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; padding: 1px 6px; border-radius: var(--radius-pill); background: var(--surface-alt); color: var(--text-muted); }
  .weight-high { background: color-mix(in srgb, var(--danger) 15%, var(--surface)); color: var(--danger); }
  .weight-medium { background: color-mix(in srgb, #ff9800 15%, var(--surface)); color: #ff9800; }
  .weight-low { background: var(--surface-alt); color: var(--text-faint); }

  .rating-cell { cursor: pointer; text-align: center; }
  .rating-cell:hover { background: var(--surface-hover); }
  .rating-cell.best { background: color-mix(in srgb, var(--success) 12%, transparent); outline: 1px solid var(--success); outline-offset: -1px; }
  .score-empty { color: var(--text-faint); }
  .note-preview { display: block; margin-top: 4px; color: var(--text-muted); font-size: 10px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .add-criterion-filler { background: transparent; }
</style>
