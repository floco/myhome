<script lang="ts">
  import type { createHouseStore } from "../houseStore.svelte";
  import type { createChoreStore } from "../choreStore.svelte";
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createCostsStore } from "../costsStore.svelte";
  import type { createWorksStore } from "../worksStore.svelte";
  import { DEFAULT_VIEWPORT } from "../viewportStore.svelte";
  import { fitViewportToFloor } from "../viewportFit";
  import Card from "./ui/Card.svelte";
  import Canvas from "./Canvas.svelte";
  import FloorSwitcher from "./FloorSwitcher.svelte";
  import LayersDropdown from "./LayersDropdown.svelte";
  import ChoreOverlay from "./ChoreOverlay.svelte";
  import InventoryOverlay from "./InventoryOverlay.svelte";
  import CostsOverlay from "./CostsOverlay.svelte";
  import WorksOverlay from "./WorksOverlay.svelte";

  type HouseStore = ReturnType<typeof createHouseStore>;
  type ChoreStore = ReturnType<typeof createChoreStore>;
  type InventoryStore = ReturnType<typeof createInventoryStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type CostsStore = ReturnType<typeof createCostsStore>;
  type WorksStore = ReturnType<typeof createWorksStore>;

  interface Props {
    floorStore: HouseStore;
    choreStore: ChoreStore;
    inventoryStore: InventoryStore;
    settingsStore: SettingsStore;
    costsStore: CostsStore;
    worksStore: WorksStore;
    onnavigate: () => void;
  }
  let { floorStore, choreStore, inventoryStore, settingsStore, costsStore: _costsStore, worksStore, onnavigate }: Props =
    $props();

  const ALL_FLOOR_ID = "__all__";

  let selectedFloorId = $state<string | null>(null);
  let activeLayers = $state<Set<string>>(new Set(["chores"]));
  let mapWidth = $state(400);
  let mapHeight = $state(240);

  const effectiveFloorId = $derived(
    selectedFloorId && floorStore.floors.some((f) => f.id === selectedFloorId)
      ? selectedFloorId
      : floorStore.floors[0]?.id ?? null
  );
  const currentFloor = $derived(floorStore.floors.find((f) => f.id === effectiveFloorId) ?? null);

  const viewport = $derived(
    currentFloor ? fitViewportToFloor(currentFloor, mapWidth, mapHeight) : DEFAULT_VIEWPORT
  );

  const floorRoomIds = $derived(new Set(currentFloor?.rooms.map((r) => r.id) ?? []));
  const floorAssignments = $derived(
    choreStore.assignments.filter((a) => a.roomId !== null && floorRoomIds.has(a.roomId))
  );
  const floorInventoryItems = $derived(
    inventoryStore.items.filter((i) => i.placement?.floorId === effectiveFloorId)
  );
  const floorCostCategories = $derived(
    settingsStore.costCategories.filter((c) => c.placement?.floorId === effectiveFloorId)
  );
  const floorWorks = $derived(
    worksStore.works.filter((w) => w.placement?.floorId === effectiveFloorId)
  );

  function handleSwitchFloor(id: string): void {
    if (id === ALL_FLOOR_ID) return;
    selectedFloorId = id;
  }

  function toggleLayer(layer: string): void {
    const next = new Set(activeLayers);
    if (next.has(layer)) next.delete(layer);
    else next.add(layer);
    activeLayers = next;
  }

  function noop(): void {}
</script>

<Card>
  <div class="map-widget-body">
    <div class="map-toolbar">
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div onclick={(e) => e.stopPropagation()}>
        <FloorSwitcher
          floors={floorStore.floors}
          currentFloorId={effectiveFloorId ?? ""}
          onswitchfloor={handleSwitchFloor}
        />
      </div>
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div onclick={(e) => e.stopPropagation()}>
        <LayersDropdown {activeLayers} ontoggle={toggleLayer} />
      </div>
    </div>

    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="map-area" bind:clientWidth={mapWidth} bind:clientHeight={mapHeight} onclick={onnavigate}>
      {#if currentFloor}
        <Canvas floor={currentFloor} {viewport} width={mapWidth} height={mapHeight} showGrid={false} />
        {#if activeLayers.has("chores")}
          <ChoreOverlay
            chores={choreStore.chores}
            assignments={floorAssignments}
            {viewport}
            choreMode={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
        {#if activeLayers.has("inventory")}
          <InventoryOverlay
            items={floorInventoryItems}
            {viewport}
            active={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
        {#if activeLayers.has("costs")}
          <CostsOverlay
            categories={floorCostCategories}
            {viewport}
            active={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
        {#if activeLayers.has("works")}
          <WorksOverlay
            works={floorWorks}
            {settingsStore}
            {viewport}
            active={false}
            width={mapWidth}
            height={mapHeight}
            onclick={noop}
            ondragend={noop}
          />
        {/if}
      {:else}
        <div class="empty">No floors yet.</div>
      {/if}
    </div>
  </div>
</Card>

<style>
  .map-widget-body { display: flex; flex-direction: column; gap: var(--space-2); }
  .map-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); flex-wrap: wrap; }
  .map-area {
    position: relative; overflow: hidden; height: 220px;
    border-radius: var(--radius-md); background: var(--canvas-bg); cursor: pointer;
  }
  .empty {
    display: flex; align-items: center; justify-content: center; height: 100%;
    color: var(--text-faint); font-size: 12px;
  }
</style>
