<script lang="ts">
  import type { ToolType } from "../toolStore.svelte";

  let {
    tool,
    hasSelection,
    onselecttool,
    ondelete,
  }: {
    tool: ToolType;
    hasSelection: boolean;
    onselecttool: (tool: ToolType) => void;
    ondelete: () => void;
  } = $props();
</script>

<nav class="toolbar">
  <button class:active={tool === "select"} onclick={() => onselecttool("select")}> Select </button>
  <button class:active={tool === "wall"} onclick={() => onselecttool("wall")}> Wall </button>
  <button class:active={tool === "divider"} onclick={() => onselecttool("divider")}> Divider </button>
  <button class="delete" disabled={!hasSelection} onclick={ondelete}> Delete </button>
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
  button {
    padding: 6px;
    border: none;
    border-radius: 4px;
    background: #444;
    color: #ccc;
    cursor: pointer;
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
