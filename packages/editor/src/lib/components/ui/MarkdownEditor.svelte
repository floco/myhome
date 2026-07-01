<script lang="ts">
  import { marked } from "marked";
  import DOMPurify from "dompurify";
  import type { MediaItem } from "./mediaTypes";

  // Single newlines become <br>; GFM adds ~~strikethrough~~, tables, task lists.
  marked.use({ breaks: true, gfm: true });

  interface Props {
    value: string;
    editing: boolean;
    placeholder?: string;
    minHeight?: string;
    mediaItems?: MediaItem[];
    clickToEdit?: boolean;
  }

  let {
    value = $bindable(),
    editing = $bindable(),
    placeholder = "Click to add markdown content…",
    minHeight = "200px",
    mediaItems = [],
    clickToEdit = true,
  }: Props = $props();

  let textareaEl: HTMLTextAreaElement | null = $state(null);
  let pickerOpen = $state(false);
  let wrapEl: HTMLElement | null = $state(null);

  // Close picker when user clicks anywhere outside .tb-media-wrap.
  $effect(() => {
    if (!pickerOpen) return;
    function handleClick(e: MouseEvent) {
      if (!wrapEl?.contains(e.target as Node)) pickerOpen = false;
    }
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  });

  // marked() is sync here (no async extensions); cast to string is safe.
  const renderedHtml = $derived(
    value.trim() ? DOMPurify.sanitize(marked(value) as string) : "",
  );

  /** Wrap the current selection (or insert placeholder text) with before/after. */
  function insert(before: string, after = "", defaultText = "") {
    if (!textareaEl) return;
    const s = textareaEl.selectionStart;
    const e = textareaEl.selectionEnd;
    const sel = value.slice(s, e) || defaultText;
    value = value.slice(0, s) + before + sel + after + value.slice(e);
    const ns = s + before.length;
    const ne = ns + sel.length;
    setTimeout(() => { if (textareaEl) { textareaEl.focus(); textareaEl.setSelectionRange(ns, ne); } }, 0);
  }

  /** Prepend prefix to the line where the cursor currently sits. */
  function linePrefix(prefix: string) {
    if (!textareaEl) return;
    const s = textareaEl.selectionStart;
    const lineStart = value.lastIndexOf("\n", s - 1) + 1;
    value = value.slice(0, lineStart) + prefix + value.slice(lineStart);
    const ns = lineStart + prefix.length;
    setTimeout(() => { if (textareaEl) { textareaEl.focus(); textareaEl.setSelectionRange(ns, ns); } }, 0);
  }

  function insertMedia(item: MediaItem, width: number): void {
    const md =
      item.type === "document"
        ? `<a href="${item.url}"><img src="${item.thumbnailUrl}" width="${width}" alt="${item.name}"></a>`
        : `<img src="${item.url}" width="${width}" alt="${item.name}">`;
    insert(md);
    pickerOpen = false;
  }
</script>

{#if editing}
  <div class="md-toolbar" role="toolbar" aria-label="Markdown formatting">
    <button class="tb-btn" type="button" title="Heading 1" onclick={() => linePrefix("# ")}>H1</button>
    <button class="tb-btn" type="button" title="Heading 2" onclick={() => linePrefix("## ")}>H2</button>
    <button class="tb-btn" type="button" title="Heading 3" onclick={() => linePrefix("### ")}>H3</button>
    <span class="tb-sep" aria-hidden="true"></span>
    <button class="tb-btn tb-bold" type="button" title="Bold" onclick={() => insert("**", "**", "bold")}>B</button>
    <button class="tb-btn tb-italic" type="button" title="Italic" onclick={() => insert("_", "_", "italic")}>I</button>
    <button class="tb-btn" type="button" title="Strikethrough" onclick={() => insert("~~", "~~", "text")}>S̶</button>
    <span class="tb-sep" aria-hidden="true"></span>
    <button class="tb-btn" type="button" title="Bullet list" onclick={() => linePrefix("- ")}>• List</button>
    <button class="tb-btn" type="button" title="Numbered list" onclick={() => linePrefix("1. ")}>1. List</button>
    <button class="tb-btn" type="button" title="Blockquote" onclick={() => linePrefix("> ")}>❝</button>
    <span class="tb-sep" aria-hidden="true"></span>
    <button class="tb-btn" type="button" title="Inline code" onclick={() => insert("`", "`", "code")}>`code`</button>
    <button class="tb-btn" type="button" title="Code block" onclick={() => insert("```\n", "\n```", "code")}>```</button>
    <span class="tb-sep" aria-hidden="true"></span>
    <button class="tb-btn" type="button" title="Link" onclick={() => insert("[", "](url)", "link text")}>🔗</button>
    <button class="tb-btn" type="button" title="Horizontal rule" onclick={() => insert("\n---\n", "", "")}>—</button>
    {#if mediaItems.length > 0}
      <span class="tb-sep" aria-hidden="true"></span>
      <div
        class="tb-media-wrap"
        role="group"
        bind:this={wrapEl}
        onkeydown={(e) => { if (e.key === "Escape") pickerOpen = false; }}
      >
        <button
          class="tb-btn"
          type="button"
          title="Insert media"
          onclick={() => { pickerOpen = !pickerOpen; }}
        >📷</button>
        {#if pickerOpen}
          <div class="media-picker" role="listbox" aria-label="Insert media attachment">
            {#each mediaItems as item (item.id)}
              <div class="media-tile" title={item.name}>
                <img src={item.thumbnailUrl} alt={item.name} />
                <span class="media-tile-name">{item.name}</span>
                <div class="media-tile-sizes">
                  <button type="button" class="size-btn" data-size="s" onclick={() => insertMedia(item, 200)}>S</button>
                  <button type="button" class="size-btn" data-size="m" onclick={() => insertMedia(item, 400)}>M</button>
                  <button type="button" class="size-btn" data-size="l" onclick={() => insertMedia(item, 600)}>L</button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
  <textarea
    class="md-editor"
    style:min-height={minHeight}
    bind:this={textareaEl}
    bind:value
    placeholder="Write in Markdown…"
  ></textarea>
{:else}
  <div
    role={clickToEdit ? "button" : undefined}
    tabindex={clickToEdit ? 0 : undefined}
    class="md-preview"
    class:md-clickable={clickToEdit}
    class:md-empty={!renderedHtml}
    style:min-height={minHeight}
    onclick={clickToEdit ? () => { editing = true; } : undefined}
    onkeydown={clickToEdit ? (e) => { if (e.key === "Enter" || e.key === " ") editing = true; } : undefined}
    title={clickToEdit ? "Click to edit" : undefined}
  >
    {#if renderedHtml}
      {@html renderedHtml}
    {:else}
      <span class="md-placeholder">{placeholder}</span>
    {/if}
  </div>
{/if}

<style>
  .md-toolbar {
    display: flex; align-items: center; gap: 2px; flex-wrap: wrap;
    padding: 4px 6px;
    background: var(--surface-hover);
    border: 1px solid var(--border); border-bottom: none;
    border-radius: var(--radius-md) var(--radius-md) 0 0;
  }
  .tb-btn {
    padding: 2px 7px; font-size: 11px; font-family: var(--font-sans);
    border: 1px solid transparent; border-radius: var(--radius-sm);
    background: none; color: var(--text-muted); cursor: pointer;
    line-height: 1.6; white-space: nowrap;
  }
  .tb-btn:hover { background: var(--surface); border-color: var(--border); color: var(--text); }
  .tb-bold { font-weight: bold; }
  .tb-italic { font-style: italic; }
  .tb-sep { width: 1px; height: 14px; background: var(--border); margin: 0 3px; flex-shrink: 0; }

  .tb-media-wrap { position: relative; display: inline-block; }
  .media-picker {
    position: absolute; top: calc(100% + 4px); left: 0; z-index: 100;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: var(--space-2);
    display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2);
    max-height: 220px; overflow-y: auto; min-width: 220px;
  }
  .media-tile {
    border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 4px;
    display: flex; flex-direction: column; align-items: center; gap: 3px;
  }
  .media-tile img {
    width: 40px; height: 40px; object-fit: cover;
    border-radius: var(--radius-sm); display: block;
  }
  .media-tile-name {
    font-size: 10px; color: var(--text-muted);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    max-width: 60px; text-align: center;
  }
  .media-tile-sizes { display: flex; gap: 2px; }
  .size-btn {
    padding: 1px 5px; font-size: 9px; font-weight: 600; font-family: var(--font-sans);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: none; color: var(--text-muted); cursor: pointer;
  }
  .size-btn:hover { background: var(--accent); color: white; border-color: var(--accent); }

  .md-editor {
    width: 100%; box-sizing: border-box;
    padding: 10px 12px; resize: vertical;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: 0 0 var(--radius-md) var(--radius-md);
    color: var(--text);
    font-family: monospace; font-size: 12px; line-height: 1.5;
  }
  .md-editor:focus { outline: none; border-color: var(--accent); }

  .md-preview {
    width: 100%; box-sizing: border-box;
    padding: 10px 12px; overflow-y: auto;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-md); cursor: default;
    color: var(--text); font-family: var(--font-sans); font-size: 13px; line-height: 1.65;
  }
  .md-preview.md-clickable { cursor: pointer; }
  .md-preview.md-clickable:hover { border-color: var(--accent); }
  .md-preview.md-empty { border-style: dashed; }

  .md-placeholder { color: var(--text-faint); font-size: 12px; font-style: italic; }

  .md-preview :global(h1) { color: var(--text); margin: 0.6em 0 0.3em; font-size: 16px; }
  .md-preview :global(h2) { color: var(--text); margin: 0.6em 0 0.3em; font-size: 14px; }
  .md-preview :global(h3) { color: var(--text); margin: 0.6em 0 0.3em; font-size: 13px; }
  .md-preview :global(p) { margin: 0.4em 0; }
  .md-preview :global(ul), .md-preview :global(ol) { margin: 0.4em 0; padding-left: 1.4em; }
  .md-preview :global(li) { margin: 0.2em 0; }
  .md-preview :global(code) {
    background: var(--surface-hover); border: 1px solid var(--border);
    border-radius: 3px; padding: 0 4px; font-size: 11px; font-family: monospace; color: var(--text);
  }
  .md-preview :global(pre) {
    background: var(--surface-hover); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 10px; overflow-x: auto; margin: 0.5em 0;
  }
  .md-preview :global(pre code) { background: none; border: none; padding: 0; }
  .md-preview :global(blockquote) {
    border-left: 3px solid var(--border); margin: 0.5em 0; padding: 2px 12px; color: var(--text-muted);
  }
  .md-preview :global(hr) { border: none; border-top: 1px solid var(--border); margin: 0.8em 0; }
  .md-preview :global(a) { color: var(--accent); }
  .md-preview :global(strong) { color: var(--text); }
  .md-preview :global(em) { color: var(--text-muted); }
  .md-preview :global(table) { border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 12px; }
  .md-preview :global(th), .md-preview :global(td) { border: 1px solid var(--border); padding: 4px 8px; }
  .md-preview :global(th) { background: var(--surface-hover); }
</style>
