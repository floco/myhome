<!-- packages/editor/src/lib/components/CommandPalette.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import { filterResults, MODULE_ORDER, type SearchResult } from "../searchIndex";

  interface Props {
    open: boolean;
    index: SearchResult[];
    onclose: () => void;
    onselect: (result: SearchResult) => void;
  }
  let { open, index, onclose, onselect }: Props = $props();

  let query = $state("");
  let highlighted = $state(0);
  let inputEl: HTMLInputElement | undefined = $state();

  const results = $derived(filterResults(index, query));

  const groups = $derived.by(() => {
    const byModule = new Map<string, SearchResult[]>();
    for (const r of results) {
      if (!byModule.has(r.module)) byModule.set(r.module, []);
      byModule.get(r.module)!.push(r);
    }
    return MODULE_ORDER
      .filter((m) => byModule.has(m))
      .map((m) => ({ module: m, label: $_(`common.modules.${m}`), items: byModule.get(m)! }));
  });

  $effect(() => {
    if (open) {
      query = "";
      highlighted = 0;
      inputEl?.focus();
    }
  });

  $effect(() => {
    results;
    highlighted = 0;
  });

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") { onclose(); return; }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (results.length > 0) highlighted = (highlighted + 1) % results.length;
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (results.length > 0) highlighted = (highlighted - 1 + results.length) % results.length;
      return;
    }
    if (e.key === "Enter") {
      const target = results[highlighted];
      if (target) onselect(target);
    }
  }

  function flatIndexOf(result: SearchResult): number {
    return results.indexOf(result);
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="cmdk-backdrop" role="presentation" onclick={onclose}></div>
  <div class="cmdk" role="dialog" aria-modal="true" aria-label={$_('common.search.ariaLabel')}>
    <input
      bind:this={inputEl}
      class="cmdk-input"
      type="text"
      placeholder={$_('common.search.placeholder')}
      bind:value={query}
      onkeydown={handleKeydown}
    />
    <div class="cmdk-results">
      {#if query.trim().length >= 2 && results.length === 0}
        <div class="cmdk-empty">{$_('common.search.noResults', { values: { query } })}</div>
      {/if}
      {#each groups as group (group.module)}
        <div class="cmdk-group-label">{group.label}</div>
        {#each group.items as result (result.id)}
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
          <div
            class="cmdk-result"
            class:highlighted={flatIndexOf(result) === highlighted}
            onclick={() => onselect(result)}
          >
            <span class="cmdk-result-icon">{result.icon}</span>
            <div class="cmdk-result-text">
              <div class="cmdk-result-title">{result.title}</div>
              <div class="cmdk-result-subtitle">{result.subtitle}</div>
            </div>
          </div>
        {/each}
      {/each}
    </div>
  </div>
{/if}

<style>
  .cmdk-backdrop {
    position: fixed; inset: 0; z-index: 199;
    background: rgba(0, 0, 0, 0.45);
  }
  .cmdk {
    position: fixed; top: 12vh; left: 50%; transform: translateX(-50%);
    z-index: 200;
    width: min(90vw, 560px);
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    display: flex; flex-direction: column;
    max-height: 70vh; overflow: hidden;
  }
  .cmdk-input {
    font-family: var(--font-sans);
    font-size: 14px;
    background: var(--surface-alt);
    color: var(--text);
    border: none;
    border-bottom: 1px solid var(--border);
    padding: 14px 16px;
    box-sizing: border-box;
  }
  .cmdk-input:focus { outline: none; }
  .cmdk-results { overflow-y: auto; padding: var(--space-2); }
  .cmdk-empty { padding: 16px; font-size: 12px; color: var(--text-faint); text-align: center; }
  .cmdk-group-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--text-faint); padding: 8px 10px 4px;
  }
  .cmdk-result {
    display: flex; align-items: center; gap: var(--space-2);
    padding: 8px 10px; border-radius: var(--radius-md); cursor: pointer;
  }
  .cmdk-result:hover, .cmdk-result.highlighted { background: var(--surface-hover); }
  .cmdk-result-icon { font-size: 16px; flex-shrink: 0; }
  .cmdk-result-title { font-size: 13px; color: var(--text); font-weight: 500; }
  .cmdk-result-subtitle { font-size: 11px; color: var(--text-faint); margin-top: 1px; }
</style>
