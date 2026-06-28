<script lang="ts">
  import type { createHouseStore } from "../houseStore.svelte";
  import type { createChoreStore } from "../choreStore.svelte";
  import type { createInventoryStore } from "../inventoryStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createCostsStore } from "../costsStore.svelte";
  import type { createWorksStore } from "../worksStore.svelte";
  import HomeMapWidget from "./HomeMapWidget.svelte";
  import HomeChoresWidget from "./HomeChoresWidget.svelte";
  import HomeCostsWidget from "./HomeCostsWidget.svelte";
  import HomeInventoryWidget from "./HomeInventoryWidget.svelte";
  import HomeWorksWidget from "./HomeWorksWidget.svelte";

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
  }
  let { floorStore, choreStore, inventoryStore, settingsStore, costsStore, worksStore }: Props = $props();

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
