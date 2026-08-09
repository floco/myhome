<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { FurnitureObject } from "@myhome/geometry";
  import type { FurnitureTemplate, FurnitureParamDef } from "../furnitureLibrary";
  import { resolveFurnitureParams } from "../furnitureLibrary";

  let {
    object,
    template,
    readOnly = false,
    onupdate,
    onstartdrag,
    ondismiss,
  }: {
    object: FurnitureObject;
    template: FurnitureTemplate;
    readOnly?: boolean;
    onupdate: (patch: Record<string, string | number>) => void;
    onstartdrag?: (e: PointerEvent) => void;
    ondismiss?: () => void;
  } = $props();

  const params = $derived(resolveFurnitureParams(template, object));

  function isEnumParam(def: FurnitureParamDef): def is Extract<FurnitureParamDef, { type: "enum" }> {
    return def.type === "enum";
  }

  function isVisible(def: FurnitureParamDef): boolean {
    if (!isEnumParam(def) || !def.visibleWhen) return true;
    return params[def.visibleWhen.paramId] === def.visibleWhen.equals;
  }

  function paramMin(def: FurnitureParamDef): number | undefined {
    return def.type === "enum" ? undefined : def.min;
  }

  function paramMax(def: FurnitureParamDef): number | undefined {
    return def.type === "enum" ? undefined : def.max;
  }

  function paramStep(def: FurnitureParamDef): number {
    return def.type === "number" ? (def.step ?? 1) : 1;
  }

  function paramUnit(def: FurnitureParamDef): string | undefined {
    return def.type === "number" ? def.unit : undefined;
  }

  function handleNumberInput(def: FurnitureParamDef, e: Event): void {
    const value = Number((e.target as HTMLInputElement).value);
    if (Number.isNaN(value)) return;
    onupdate({ [def.id]: value });
  }

  function handleEnumChange(def: FurnitureParamDef, e: Event): void {
    onupdate({ [def.id]: (e.target as HTMLSelectElement).value });
  }
</script>

<aside class="furniture-params-panel">
  <div class="panel-header">
    {#if onstartdrag}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drag-handle" onpointerdown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
    {/if}
    <h2>{$_(`floorPlan.furnitureLibrary.items.${template.id}`)}</h2>
    {#if ondismiss}
      <button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>
    {/if}
  </div>

  {#each template.params ?? [] as def (def.id)}
    {#if isVisible(def)}
      <label>
        <span>{$_(def.labelKey)}{#if paramUnit(def)} ({paramUnit(def)}){/if}</span>
        {#if isEnumParam(def)}
          <select value={params[def.id]} disabled={readOnly} onchange={(e) => handleEnumChange(def, e)}>
            {#each def.options as opt (opt.value)}
              <option value={opt.value}>{$_(opt.labelKey)}</option>
            {/each}
          </select>
        {:else}
          <input
            type="number"
            min={paramMin(def)}
            max={paramMax(def)}
            step={paramStep(def)}
            value={params[def.id]}
            disabled={readOnly}
            oninput={(e) => handleNumberInput(def, e)}
          />
        {/if}
      </label>
    {/if}
  {/each}
</aside>

<style>
  .furniture-params-panel {
    width: 200px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    overflow-y: auto;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .furniture-params-panel {
      width: 100%;
      height: 100%;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
    }
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  h2 {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
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
  .dismiss-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    flex-shrink: 0;
    padding: 2px 4px;
    border-radius: var(--radius-sm);
  }
  .dismiss-btn:hover { background: var(--surface-hover); color: var(--text); }
  label {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  span {
    font-size: 11px;
    color: var(--text-muted);
  }
  input,
  select {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 4px 6px;
    font-size: 12px;
    font-family: inherit;
  }
  input:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
  }
</style>
