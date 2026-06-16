<script lang="ts">
  import type { ToolType } from "../toolStore.svelte";

  let {
    tool,
    hasSelection,
    hasUndo = false,
    hasRedo = false,
    onselecttool,
    ondelete,
    onundo,
    onredo,
  }: {
    tool: ToolType;
    hasSelection: boolean;
    hasUndo?: boolean;
    hasRedo?: boolean;
    onselecttool: (tool: ToolType) => void;
    ondelete: () => void;
    onundo?: () => void;
    onredo?: () => void;
  } = $props();
</script>

<nav class="toolbar">
  <button disabled={!hasUndo} onclick={() => onundo?.()}>Undo</button>
  <button disabled={!hasRedo} onclick={() => onredo?.()}>Redo</button>
  <hr />
  <button class:active={tool === "select"} onclick={() => onselecttool("select")}>Select</button>
  <button class:active={tool === "wall"} onclick={() => onselecttool("wall")}>Wall</button>
  <button class:active={tool === "divider"} onclick={() => onselecttool("divider")}>Divider</button>
  <button class:active={tool === "door"} onclick={() => onselecttool("door")}>Door</button>
  <button class:active={tool === "window"} onclick={() => onselecttool("window")}>Window</button>
  <button class="delete" disabled={!hasSelection} onclick={ondelete}>Delete</button>
</nav>

<style>
  .toolbar {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 6px;
    background: #333;
    width: 64px;
  }
  hr {
    border: none;
    border-top: 1px solid #555;
    margin: 0;
  }
  button {
    padding: 6px;
    border: none;
    border-radius: 4px;
    background: #444;
    color: #ccc;
    cursor: pointer;
    font-size: 11px;
  }
  button.active {
    background: #555;
    color: #eee;
  }
  button.delete {
    margin-top: auto;
    background: #622;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
