<script lang="ts">
  import { createFloorStore } from "./lib/floorStore.svelte";
  import { createViewportStore } from "./lib/viewportStore.svelte";
  import { createToolStore } from "./lib/toolStore.svelte";
  import Canvas from "./lib/components/Canvas.svelte";
  import Toolbar from "./lib/components/Toolbar.svelte";

  const floorStore = createFloorStore();
  const viewportStore = createViewportStore();
  const toolStore = createToolStore();

  function handleSelect(id: string | null): void {
    if (toolStore.state.tool === "select") {
      toolStore.select(id);
    }
  }

  function handleDelete(): void {
    const id = toolStore.state.selectedId;
    if (id) {
      floorStore.removeWall(id);
      toolStore.select(null);
    }
  }

  function handleKeydown(event: KeyboardEvent): void {
    if ((event.key === "Delete" || event.key === "Backspace") && toolStore.state.selectedId) {
      handleDelete();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="app">
  <header class="topbar">
    <h1>Floor Plan Editor</h1>
  </header>
  <div class="body">
    <Toolbar
      tool={toolStore.state.tool}
      hasSelection={toolStore.state.selectedId !== null}
      onselecttool={(tool) => toolStore.setTool(tool)}
      ondelete={handleDelete}
    />
    <Canvas
      floor={floorStore.floor}
      viewport={viewportStore.viewport}
      width={1200}
      height={800}
      selectedId={toolStore.state.selectedId}
      onselect={handleSelect}
    />
  </div>
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    font-family: sans-serif;
  }
  .topbar {
    height: 32px;
    background: #2a2a2a;
    color: #ccc;
    display: flex;
    align-items: center;
    padding: 0 12px;
    flex-shrink: 0;
  }
  .topbar h1 {
    font-size: 14px;
    margin: 0;
    font-weight: 600;
  }
  .body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
</style>
