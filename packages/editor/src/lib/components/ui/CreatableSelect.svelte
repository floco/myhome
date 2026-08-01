<script lang="ts">
  import { _ } from "svelte-i18n";

  interface Option {
    id: string;
    name: string;
  }

  interface Props {
    value: string | null;
    options: Option[];
    placeholder?: string;
    oncreate: (name: string) => Promise<Option>;
    onchange?: (id: string | null) => void;
  }

  let { value = $bindable(), options, placeholder = "", oncreate, onchange }: Props = $props();

  let open = $state(false);
  let query = $state("");
  let wrapper = $state<HTMLElement | null>(null);
  let panelEl = $state<HTMLElement | null>(null);
  let triggerEl = $state<HTMLInputElement | null>(null);
  let panelLeft = $state(0);
  let panelTop = $state(0);
  let panelWidth = $state(0);
  let highlightIndex = $state(0);
  let creating = $state(false);

  const selectedName = $derived(options.find((o) => o.id === value)?.name ?? "");
  const displayValue = $derived(open ? query : selectedName);

  const filtered = $derived(
    options.filter((o) => o.name.toLowerCase().includes(query.trim().toLowerCase()))
  );
  const exactMatch = $derived(
    filtered.some((o) => o.name.toLowerCase() === query.trim().toLowerCase())
  );
  const showCreateRow = $derived(query.trim().length > 0 && !exactMatch);

  // Teleport the panel to <body> so position:fixed isn't affected by
  // ancestor CSS transforms (e.g. Modal uses translate(-50%,-50%)) --
  // same mechanism as EmojiPicker.svelte's portal action.
  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  function openPanel(): void {
    if (triggerEl) {
      const rect = triggerEl.getBoundingClientRect();
      panelLeft = rect.left;
      panelTop = rect.bottom + 4;
      panelWidth = rect.width;
    }
    query = "";
    open = true;
    highlightIndex = 0;
  }

  function closePanel(): void {
    open = false;
    query = "";
  }

  function selectOption(o: Option): void {
    value = o.id;
    onchange?.(o.id);
    closePanel();
  }

  async function createFromQuery(): Promise<void> {
    const name = query.trim();
    if (!name || creating) return;
    creating = true;
    try {
      const created = await oncreate(name);
      value = created.id;
      onchange?.(created.id);
      closePanel();
    } finally {
      creating = false;
    }
  }

  function handleInput(e: Event): void {
    query = (e.target as HTMLInputElement).value;
    highlightIndex = 0;
    if (!open) openPanel();
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") { closePanel(); return; }
    const total = filtered.length + (showCreateRow ? 1 : 0);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (total > 0) highlightIndex = (highlightIndex + 1) % total;
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (total > 0) highlightIndex = (highlightIndex - 1 + total) % total;
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (highlightIndex < filtered.length) {
        if (filtered[highlightIndex]) selectOption(filtered[highlightIndex]);
      } else if (showCreateRow) {
        createFromQuery();
      }
    }
  }

  function handleClickOutside(e: MouseEvent): void {
    const target = e.target as Node;
    if (wrapper?.contains(target) || panelEl?.contains(target)) return;
    closePanel();
  }

  function clearValue(): void {
    value = null;
    onchange?.(null);
    query = "";
  }
</script>

<svelte:window onclick={handleClickOutside} />

<span class="cs-wrap" bind:this={wrapper}>
  <input
    class="cs-input"
    bind:this={triggerEl}
    value={displayValue}
    {placeholder}
    oninput={handleInput}
    onfocus={openPanel}
    onkeydown={handleKeydown}
  />
  {#if value && !open}
    <button type="button" class="cs-clear" onclick={clearValue}>✕</button>
  {/if}

  {#if open}
    <div class="cs-panel" style="left:{panelLeft}px;top:{panelTop}px;min-width:{panelWidth}px" bind:this={panelEl} use:portal>
      {#each filtered as o, i}
        <button
          type="button"
          class="cs-option"
          class:highlighted={i === highlightIndex}
          onclick={() => selectOption(o)}
        >
          {o.name}
        </button>
      {/each}
      {#if showCreateRow}
        <button
          type="button"
          class="cs-option cs-create"
          class:highlighted={highlightIndex === filtered.length}
          disabled={creating}
          onclick={createFromQuery}
        >
          {$_('common.createOption', { values: { name: query.trim() } })}
        </button>
      {/if}
    </div>
  {/if}
</span>

<style>
  .cs-wrap { position: relative; display: inline-flex; align-items: center; width: 100%; }
  .cs-input {
    width: 100%; background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 28px 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box;
  }
  .cs-input:focus { outline: none; border-color: var(--accent); }
  .cs-clear {
    position: absolute; right: 6px; background: none; border: none; color: var(--text-faint);
    cursor: pointer; font-size: 11px; padding: 2px;
  }
  .cs-clear:hover { color: var(--danger); }
  .cs-panel {
    position: fixed; z-index: 9999; background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md); max-height: 220px; overflow-y: auto;
    padding: 4px;
  }
  .cs-option {
    display: block; width: 100%; text-align: left; background: none; border: none; color: var(--text);
    font-size: 13px; padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer;
    font-family: var(--font-sans);
  }
  .cs-option:hover, .cs-option.highlighted { background: var(--surface-hover); }
  .cs-create { color: var(--accent); }
</style>
