<script lang="ts">
  import { marked } from "marked";
  import DOMPurify from "dompurify";

  interface Props {
    value: string;
    editing: boolean;
    placeholder?: string;
    minHeight?: string;
  }

  let {
    value = $bindable(),
    editing = $bindable(),
    placeholder = "Click to add markdown content…",
    minHeight = "200px",
  }: Props = $props();

  // marked() is sync here (no async extensions); cast to string is safe.
  const renderedHtml = $derived(
    value.trim() ? DOMPurify.sanitize(marked(value) as string) : "",
  );
</script>

{#if editing}
  <textarea
    class="md-editor"
    style:min-height={minHeight}
    bind:value
    placeholder="Write in Markdown…"
  ></textarea>
{:else}
  <div
    role="button"
    tabindex="0"
    class="md-preview"
    class:md-empty={!renderedHtml}
    style:min-height={minHeight}
    onclick={() => { editing = true; }}
    onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") editing = true; }}
    title="Click to edit"
  >
    {#if renderedHtml}
      {@html renderedHtml}
    {:else}
      <span class="md-placeholder">{placeholder}</span>
    {/if}
  </div>
{/if}

<style>
  .md-editor {
    width: 100%; box-sizing: border-box;
    padding: 10px 12px; resize: vertical;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-md); color: var(--text);
    font-family: monospace; font-size: 12px; line-height: 1.5;
  }
  .md-editor:focus { outline: none; border-color: var(--accent); }

  .md-preview {
    width: 100%; box-sizing: border-box;
    padding: 10px 12px; overflow-y: auto;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-md); cursor: pointer;
    color: var(--text); font-family: var(--font-sans); font-size: 13px; line-height: 1.65;
  }
  .md-preview:hover { border-color: var(--accent); }
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
