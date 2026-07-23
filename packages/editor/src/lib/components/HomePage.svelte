<script lang="ts">
  import type { createHouseStore } from "../houseStore.svelte";
  import type { createChoreStore } from "../choreStore.svelte";
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createCostsStore } from "../costsStore.svelte";
  import type { createWorksStore } from "../worksStore.svelte";
  import type { createConsumableStore } from "../consumableStore.svelte";
  import type { createLocationsStore } from "../locationsStore.svelte";
  import type { createPropertiesStore } from "../propertiesStore.svelte";
  import type { createBuildStore } from "../buildStore.svelte";
  import HomeMapWidget from "./HomeMapWidget.svelte";
  import HomeChoresWidget from "./HomeChoresWidget.svelte";
  import HomeCostsWidget from "./HomeCostsWidget.svelte";
  import HomeInventoryWidget from "./HomeInventoryWidget.svelte";
  import HomeWorksWidget from "./HomeWorksWidget.svelte";
  import HomeConsumablesWidget from "./HomeConsumablesWidget.svelte";
  import HomeLocationsWidget from "./HomeLocationsWidget.svelte";
  import HomePropertiesWidget from "./HomePropertiesWidget.svelte";
  import HomeBuildWidget from "./HomeBuildWidget.svelte";

  type HouseStore = ReturnType<typeof createHouseStore>;
  type ChoreStore = ReturnType<typeof createChoreStore>;
  type InventoryStore = ReturnType<typeof createInventoryStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type CostsStore = ReturnType<typeof createCostsStore>;
  type WorksStore = ReturnType<typeof createWorksStore>;
  type ConsumableStore = ReturnType<typeof createConsumableStore>;
  type LocationsStore = ReturnType<typeof createLocationsStore>;
  type PropertiesStore = ReturnType<typeof createPropertiesStore>;
  type BuildStore = ReturnType<typeof createBuildStore>;

  interface Props {
    floorStore: HouseStore;
    choreStore: ChoreStore;
    inventoryStore: InventoryStore;
    settingsStore: SettingsStore;
    costsStore: CostsStore;
    worksStore: WorksStore;
    consumableStore: ConsumableStore;
    locationsStore: LocationsStore;
    propertiesStore: PropertiesStore;
    buildStore: BuildStore;
  }
  let { floorStore, choreStore, inventoryStore, settingsStore, costsStore, worksStore, consumableStore, locationsStore, propertiesStore, buildStore }: Props = $props();

  function navigate(hash: string): void {
    window.location.hash = hash;
  }
</script>

<div class="home-page">
  <div class="col-main">
    <HomeMapWidget
      {floorStore}
      {choreStore}
      {inventoryStore}
      {settingsStore}
      {costsStore}
      {worksStore}
      onnavigate={() => navigate("#/plan")}
    />
    <HomeChoresWidget store={choreStore} onnavigate={() => navigate("#/chores")} />
  </div>
  <div class="col-side">
    <HomeCostsWidget {costsStore} {settingsStore} onnavigate={() => navigate("#/costs")} />
    <HomeInventoryWidget {inventoryStore} onnavigate={() => navigate("#/inventory")} />
    <HomeWorksWidget {worksStore} onnavigate={() => navigate("#/works")} />
    <HomeConsumablesWidget {consumableStore} onnavigate={() => navigate("#/consumables")} />
    <HomeLocationsWidget {locationsStore} onnavigate={() => navigate("#/locations")} />
    <HomePropertiesWidget {propertiesStore} onnavigate={() => navigate("#/properties")} />
    <HomeBuildWidget {buildStore} onnavigate={() => navigate("#/build")} />
  </div>
</div>

<style>
  .home-page {
    height: 100%;
    overflow-y: auto;
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: var(--space-4);
    padding: var(--space-4);
    box-sizing: border-box;
  }
  .col-main, .col-side {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    min-width: 0;
  }

  @media (max-width: 600px) {
    .home-page { grid-template-columns: 1fr; }
  }
</style>
