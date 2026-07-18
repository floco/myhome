<script lang="ts">
  import type { createLocationsStore, Location, LocationCriterion, Weight } from "../locationsStore.svelte";
  import { ratingFor, bestScoreForCriterion } from "../locationsStore.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import LocationRatingPopup from "./LocationRatingPopup.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;
  interface Props { store: LocationsStore; }
  let { store }: Props = $props();

  const SCORE_COLOR: Record<number, string> = {
    1: "var(--danger)", 2: "#ff9800", 3: "#ffc107", 4: "#8bc34a", 5: "var(--success)",
  };
  const WEIGHT_LABEL: Record<Weight, string> = { low: "Low", medium: "Med", high: "High" };

  let newCriterionName = $state("");
  let newLocationName = $state("");
  let newLocationEmoji = $state("📍");

  let editingCriterionId = $state<string | null>(null);
  let editCriterionName = $state("");
  let editCriterionDescription = $state("");
  let editCriterionWeight = $state<Weight>("medium");
  let confirmDeleteCriterionId = $state<string | null>(null);

  let editingLocationId = $state<string | null>(null);
  let editLocationName = $state("");
  let editLocationEmoji = $state("📍");
  let confirmDeleteLocationId = $state<string | null>(null);

  let openCell = $state<{ locationId: string; criterionId: string; anchorX: number; anchorY: number } | null>(null);

  function startEditCriterion(c: LocationCriterion): void {
    editingCriterionId = c.id;
    editCriterionName = c.name;
    editCriterionDescription = c.description;
    editCriterionWeight = c.weight;
  }

  async function saveCriterion(): Promise<void> {
    if (!editingCriterionId) return;
    await store.updateCriterion(editingCriterionId, {
      name: editCriterionName, description: editCriterionDescription, weight: editCriterionWeight,
    });
    editingCriterionId = null;
  }

  async function addCriterion(): Promise<void> {
    const name = newCriterionName.trim();
    if (!name) return;
    await store.createCriterion({ name, description: "", weight: "medium" });
    newCriterionName = "";
  }

  async function moveCriterion(id: string, dir: -1 | 1): Promise<void> {
    const ids = store.criteria.map((c) => c.id);
    const idx = ids.indexOf(id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= ids.length) return;
    [ids[idx], ids[swapWith]] = [ids[swapWith], ids[idx]];
    await store.reorderCriteria(ids);
  }

  function startEditLocation(l: Location): void {
    editingLocationId = l.id;
    editLocationName = l.name;
    editLocationEmoji = l.emoji;
  }

  async function saveLocation(): Promise<void> {
    if (!editingLocationId) return;
    await store.updateLocation(editingLocationId, { name: editLocationName, emoji: editLocationEmoji });
    editingLocationId = null;
  }

  async function addLocation(): Promise<void> {
    const name = newLocationName.trim();
    if (!name) return;
    await store.createLocation({ name, emoji: newLocationEmoji });
    newLocationName = "";
    newLocationEmoji = "📍";
  }

  async function moveLocation(id: string, dir: -1 | 1): Promise<void> {
    const ids = store.locations.map((l) => l.id);
    const idx = ids.indexOf(id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= ids.length) return;
    [ids[idx], ids[swapWith]] = [ids[swapWith], ids[idx]];
    await store.reorderLocations(ids);
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

<div class="matrix-wrapper">
  <table class="matrix">
    <thead>
      <tr>
        <th class="corner">Criteria</th>
        {#each store.locations as loc (loc.id)}
          <th class="location-header">
            {#if editingLocationId === loc.id}
              <div class="edit-form">
                <EmojiPicker bind:value={editLocationEmoji} />
                <input class="edit-input" bind:value={editLocationName} />
                <button class="icon-btn" onclick={saveLocation} title="Save">✓</button>
                <button class="icon-btn" onclick={() => { editingLocationId = null; }} title="Cancel">✕</button>
              </div>
            {:else if confirmDeleteLocationId === loc.id}
              <div class="header-content">
                <span class="confirm-text">Delete {loc.name}?</span>
                <div class="header-actions">
                  <button class="icon-btn" onclick={() => { store.deleteLocation(loc.id); confirmDeleteLocationId = null; }} title="Confirm delete">✓</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteLocationId = null; }} title="Cancel">✕</button>
                </div>
              </div>
            {:else}
              <div class="header-content">
                <span class="loc-emoji">{loc.emoji}</span>
                <span class="loc-name">{loc.name}</span>
                <div class="header-actions">
                  <button class="icon-btn" onclick={() => moveLocation(loc.id, -1)} title="Move left">◀</button>
                  <button class="icon-btn" onclick={() => moveLocation(loc.id, 1)} title="Move right">▶</button>
                  <button class="icon-btn" onclick={() => startEditLocation(loc)} title="Edit">✏️</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteLocationId = loc.id; }} title="Delete">🗑</button>
                </div>
              </div>
            {/if}
          </th>
        {/each}
        <th class="add-header">
          <div class="add-form">
            <EmojiPicker bind:value={newLocationEmoji} />
            <input
              class="edit-input"
              placeholder="New location…"
              bind:value={newLocationName}
              onkeydown={(e) => { if (e.key === "Enter") addLocation(); }}
            />
            <button class="add-btn" onclick={addLocation} title="Add location">＋</button>
          </div>
        </th>
      </tr>
    </thead>
    <tbody>
      {#each store.criteria as criterion (criterion.id)}
        {@const best = bestScoreForCriterion(store.locations, store.ratings, criterion.id)}
        <tr>
          <td class="criterion-cell">
            {#if editingCriterionId === criterion.id}
              <div class="edit-form-col">
                <input class="edit-input" bind:value={editCriterionName} />
                <textarea class="edit-textarea" bind:value={editCriterionDescription}></textarea>
                <select class="native-select" bind:value={editCriterionWeight}>
                  <option value="low">Low weight</option>
                  <option value="medium">Medium weight</option>
                  <option value="high">High weight</option>
                </select>
                <div class="row-actions">
                  <button class="icon-btn" onclick={saveCriterion} title="Save">✓</button>
                  <button class="icon-btn" onclick={() => { editingCriterionId = null; }} title="Cancel">✕</button>
                </div>
              </div>
            {:else if confirmDeleteCriterionId === criterion.id}
              <div class="criterion-content">
                <span class="confirm-text">Delete {criterion.name}?</span>
                <div class="row-actions">
                  <button class="icon-btn" onclick={() => { store.deleteCriterion(criterion.id); confirmDeleteCriterionId = null; }} title="Confirm delete">✓</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteCriterionId = null; }} title="Cancel">✕</button>
                </div>
              </div>
            {:else}
              <div class="criterion-content">
                <div class="criterion-title-row">
                  <span class="criterion-name">{criterion.name}</span>
                  <span class="weight-tag weight-{criterion.weight}">{WEIGHT_LABEL[criterion.weight]}</span>
                </div>
                {#if criterion.description}<p class="criterion-desc">{criterion.description}</p>{/if}
                <div class="row-actions">
                  <button class="icon-btn" onclick={() => moveCriterion(criterion.id, -1)} title="Move up">▲</button>
                  <button class="icon-btn" onclick={() => moveCriterion(criterion.id, 1)} title="Move down">▼</button>
                  <button class="icon-btn" onclick={() => startEditCriterion(criterion)} title="Edit">✏️</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteCriterionId = criterion.id; }} title="Delete">🗑</button>
                </div>
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
                <span class="score-badge" style="background:{SCORE_COLOR[rating.score]}">{rating.score}</span>
                {#if rating.note}<span class="note-preview">{rating.note}</span>{/if}
              {:else}
                <span class="score-empty">—</span>
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
      <tr>
        <td class="add-criterion-cell">
          <input
            class="edit-input"
            placeholder="New criterion…"
            bind:value={newCriterionName}
            onkeydown={(e) => { if (e.key === "Enter") addCriterion(); }}
          />
          <button class="add-btn" onclick={addCriterion} title="Add criterion">＋</button>
        </td>
        {#each store.locations as loc (loc.id)}
          <td class="add-criterion-filler"></td>
        {/each}
      </tr>
    </tbody>
  </table>
</div>

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
  .edit-form, .add-form { display: flex; align-items: center; gap: 4px; }
  .edit-form-col { display: flex; flex-direction: column; gap: 4px; }
  .edit-input { flex: 1; background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text); padding: 4px 6px; font-size: 12px; font-family: var(--font-sans); box-sizing: border-box; }
  .edit-textarea { background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text); padding: 4px 6px; font-size: 12px; font-family: var(--font-sans); resize: vertical; min-height: 40px; }
  .native-select { background: var(--surface-alt); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-sm); padding: 4px 6px; font-size: 12px; font-family: var(--font-sans); }
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
  .score-badge { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; color: #fff; font-weight: 700; font-size: 11px; }
  .score-empty { color: var(--text-faint); }
  .note-preview { display: block; margin-top: 4px; color: var(--text-muted); font-size: 10px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .add-criterion-cell { display: flex; align-items: center; gap: 4px; }
  .add-criterion-filler { background: transparent; }
</style>
