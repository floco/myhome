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
  <button title="Undo (Ctrl+Z)" disabled={!hasUndo} onclick={() => onundo?.()}>↩</button>
  <button title="Redo (Ctrl+Y)" disabled={!hasRedo} onclick={() => onredo?.()}>↪</button>
  <div class="sep"></div>
  <button title="Select" class:active={tool === "select"} onclick={() => onselecttool("select")}>↖</button>
  <button title="Wall" class:active={tool === "wall"} onclick={() => onselecttool("wall")}>▬</button>
  <button title="Divider" class:active={tool === "divider"} onclick={() => onselecttool("divider")}>┅</button>
  <button title="Door" class:active={tool === "door"} onclick={() => onselecttool("door")}>⊓</button>
  <button title="Window" class:active={tool === "window"} onclick={() => onselecttool("window")}>⊡</button>
  <div class="sep"></div>
  <button class="delete" title="Delete selected (Del)" disabled={!hasSelection} onclick={ondelete}>✕</button>
</nav>

<style>
  .toolbar {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 2px;
    padding: var(--space-1) var(--space-2);
    background: var(--surface-alt);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    height: 36px;
    box-sizing: border-box;
  }
  .sep {
    width: 1px;
    height: 18px;
    background: var(--border);
    margin: 0 4px;
    flex-shrink: 0;
  }
  button {
    width: 30px;
    height: 28px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    padding: 0;
  }
  button:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  button.active { background: var(--accent); color: var(--accent-contrast); }
  button.delete { color: var(--danger); }
  button.delete:hover:not(:disabled) { background: var(--surface-hover); color: var(--danger); }
  button:disabled { opacity: 0.35; cursor: default; }
</style>
