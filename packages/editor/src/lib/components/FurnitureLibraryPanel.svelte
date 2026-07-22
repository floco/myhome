<script lang="ts">
  import { _ } from "svelte-i18n";
  import {
    FURNITURE_TEMPLATES,
    FURNITURE_CATEGORIES,
    type FurnitureCategory,
    type FurnitureTemplate,
  } from "../furnitureLibrary";

  let { onstartdrag }: { onstartdrag?: (e: MouseEvent) => void } = $props();

  let search = $state("");

  function templateLabel(id: string): string {
    return $_(`floorPlan.furnitureLibrary.items.${id}`);
  }

  function categoryLabel(cat: FurnitureCategory): string {
    return $_(`floorPlan.furnitureLibrary.categories.${cat}`);
  }

  const filtered = $derived(
    search.trim()
      ? FURNITURE_TEMPLATES.filter((t) =>
          templateLabel(t.id).toLowerCase().includes(search.toLowerCase()),
        )
      : FURNITURE_TEMPLATES,
  );

  function templatesForCategory(cat: FurnitureCategory): FurnitureTemplate[] {
    return filtered.filter((t) => t.category === cat);
  }

  function onDragStart(e: DragEvent, templateId: string) {
    e.dataTransfer?.setData("furnitureTemplateId", templateId);
  }
</script>

<div class="furniture-panel">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="panel-header">
    {#if onstartdrag}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drag-handle" onmousedown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
    {/if}
    <input
      type="search"
      placeholder={$_('floorPlan.furnitureLibrary.searchPlaceholder')}
      bind:value={search}
      oninput={() => {}}
    />
  </div>

  <div class="panel-body">
    {#each FURNITURE_CATEGORIES as cat}
      {@const items = templatesForCategory(cat)}
      {#if items.length > 0}
        <div class="category-section">
          <div class="category-label">{categoryLabel(cat)}</div>
          <div class="category-items">
            {#each items as template}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="furniture-item"
                draggable="true"
                data-template-id={template.id}
                ondragstart={(e) => onDragStart(e, template.id)}
                title={templateLabel(template.id)}
              >
                <svg viewBox="0 0 100 100" width="48" height="48">
                  {@html template.svgContent}
                </svg>
                <span class="item-label">{templateLabel(template.id)}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/each}
  </div>
</div>

<style>
  .furniture-panel {
    width: 200px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: var(--space-2);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .drag-handle {
    cursor: grab;
    color: var(--text-muted);
    font-size: 14px;
    letter-spacing: 3px;
    opacity: 0.5;
    padding: 2px 0;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
    user-select: none;
  }
  .drag-handle:hover { opacity: 1; background: var(--surface-hover); }
  .drag-handle:active { cursor: grabbing; }

  .panel-header input {
    flex: 1;
    min-width: 0;
    box-sizing: border-box;
    padding: 4px 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface-alt);
    color: var(--text);
    font-size: 12px;
  }

  .panel-body {
    overflow-y: auto;
    flex: 1;
    padding: var(--space-2) 0;
  }

  .category-section {
    margin-bottom: var(--space-2);
  }

  .category-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    padding: 4px var(--space-2) 2px;
  }

  .category-items {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    padding: 2px var(--space-2);
  }

  .furniture-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 2px;
    padding: 4px;
    border-radius: var(--radius-sm);
    cursor: grab;
    user-select: none;
    min-height: 64px;
  }

  .furniture-item:hover {
    background: var(--surface-hover);
  }

  .furniture-item svg {
    fill: var(--canvas-furniture-fill, #ede9e0);
    stroke: var(--canvas-furniture-stroke, #8a7f6e);
    stroke-width: 2;
  }

  .item-label {
    font-size: 10px;
    color: var(--text-muted);
    text-align: center;
    line-height: 1.2;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
