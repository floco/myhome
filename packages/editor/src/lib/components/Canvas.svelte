<script lang="ts">
  import type { Floor } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte";
  import Grid from "./Grid.svelte";
  import WallShape from "./WallShape.svelte";
  import DividerShape from "./DividerShape.svelte";
  import RoomShape from "./RoomShape.svelte";

  let {
    floor,
    viewport,
    width,
    height,
    selectedId = null,
    onselect,
  }: {
    floor: Floor;
    viewport: ViewportState;
    width: number;
    height: number;
    selectedId?: string | null;
    onselect?: (id: string | null) => void;
  } = $props();

  function handleClick(): void {
    onselect?.(null);
  }
</script>

<svg {width} {height} class="canvas" onclick={handleClick}>
  <Grid {viewport} {width} {height} />
  {#each floor.rooms as room (room.id)}
    <RoomShape {room} {viewport} />
  {/each}
  {#each floor.walls as wall (wall.id)}
    {#if wall.type === "wall"}
      <WallShape {wall} {viewport} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {:else}
      <DividerShape {wall} {viewport} selected={wall.id === selectedId} onselect={(id) => onselect?.(id)} />
    {/if}
  {/each}
</svg>

<style>
  .canvas {
    background: #1c1c1c;
    display: block;
  }
</style>
