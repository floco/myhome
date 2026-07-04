<script lang="ts">
  import type { FurnitureObject } from "@myhome/geometry";
  import type { ViewportState } from "../viewportStore.svelte.ts";
  import type { FurnitureTemplate } from "../furnitureLibrary";
  import { worldToScreen } from "../viewportStore.svelte.ts";

  let {
    object,
    template,
    viewport,
    selected = false,
    tool = "select",
    onselect,
    onbodymousedown,
  }: {
    object: FurnitureObject;
    template: FurnitureTemplate;
    viewport: ViewportState;
    selected?: boolean;
    tool?: string;
    onselect?: (id: string) => void;
    onbodymousedown?: (id: string, e: MouseEvent) => void;
  } = $props();

  const cs = $derived(worldToScreen({ x: object.x, y: object.y }, viewport));
  const scaleX = $derived((object.width * viewport.zoom) / 100);
  const scaleY = $derived((object.height * viewport.zoom) / 100);

  function handleClick(e: MouseEvent) {
    e.stopPropagation();
    onselect?.(object.id);
  }

  function handleMousedown(e: MouseEvent) {
    onbodymousedown?.(object.id, e);
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<g
  class="furniture-object"
  class:selected
  transform="translate({cs.x},{cs.y}) rotate({object.rotation}) scale({scaleX},{scaleY}) translate(-50,-50)"
  onclick={handleClick}
  onmousedown={handleMousedown}
  role="button"
  tabindex="-1"
  aria-label={template.label}
>
  {@html template.svgContent}
</g>

<style>
  .furniture-object {
    fill: var(--canvas-furniture-fill);
    stroke: var(--canvas-furniture-stroke);
    stroke-width: 2;
    cursor: grab;
    vector-effect: non-scaling-stroke;
  }

  .furniture-object.selected {
    stroke: var(--canvas-wall-selected, #111);
    stroke-width: 2.5;
  }

  .furniture-object :global(line),
  .furniture-object :global(path) {
    stroke: var(--canvas-furniture-stroke);
  }
</style>
