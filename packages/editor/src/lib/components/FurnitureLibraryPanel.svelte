<script lang="ts">
  import {
    FURNITURE_TEMPLATES,
    FURNITURE_CATEGORIES,
    CATEGORY_LABELS,
    type FurnitureCategory,
    type FurnitureTemplate,
  } from "../furnitureLibrary";

  let search = $state("");

  const filtered = $derived(
    search.trim()
      ? FURNITURE_TEMPLATES.filter((t) =>
          t.label.toLowerCase().includes(search.toLowerCase()),
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
  <div class="panel-header">
    <input
      type="search"
      placeholder="Search objects..."
      bind:value={search}
      oninput={() => {}}
    />
  </div>

  <div class="panel-body">
    {#each FURNITURE_CATEGORIES as cat}
      {@const items = templatesForCategory(cat)}
      {#if items.length > 0}
        <div class="category-section">
          <div class="category-label">{CATEGORY_LABELS[cat]}</div>
          <div class="category-items">
            {#each items as template}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="furniture-item"
                draggable="true"
                data-template-id={template.id}
                ondragstart={(e) => onDragStart(e, template.id)}
                title={template.label}
              >
                <svg viewBox="0 0 100 100" width="44" height="44">
                  {@html template.svgContent}
                </svg>
                <span class="item-label">{template.label}</span>
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
    width: 180px;
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--surface);
    border-left: 1px solid var(--border);
    overflow: hidden;
  }

  .panel-header {
    padding: var(--space-2);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .panel-header input {
    width: 100%;
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
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 2px var(--space-2);
  }

  .furniture-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 4px;
    border-radius: var(--radius-sm);
    cursor: grab;
    user-select: none;
    width: 68px;
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
    max-width: 60px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
