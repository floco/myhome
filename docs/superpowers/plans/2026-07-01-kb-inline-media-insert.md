# KB Inline Media Insert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 📷 toolbar button to `MarkdownEditor` that opens a floating picker panel listing the entry's uploaded attachments; clicking a tile inserts `![name](url)` (image) or `[![name](thumb)](url)` (PDF) at the cursor and closes the picker.

**Architecture:** `MarkdownEditor` gains an optional `mediaItems?: MediaItem[]` prop — when non-empty, a 📷 button and floating picker panel appear at the right end of the toolbar. `KBPage` passes `mediaItems` (already derived from `selectedEntry.attachments`) to the editor when the Content tab is active, passing `[]` otherwise so the button hides on the Media tab.

**Tech Stack:** Svelte 5 (`$state`, `$effect`, `$bindable`, `$props`), Vitest + jsdom (`mount`/`unmount`/`flushSync`), TypeScript

---

## File Map

| File | Change |
|------|--------|
| `packages/editor/test/MarkdownEditor.test.ts` | Add `describe("MarkdownEditor — media picker")` with 8 tests |
| `packages/editor/src/lib/components/ui/MarkdownEditor.svelte` | Add `mediaItems` prop, `pickerOpen` state, `wrapEl` ref, `$effect` for click-outside, `insertMedia()`, picker button + panel in toolbar, CSS |
| `packages/editor/test/KBPage.test.ts` | Add `describe("KBPage — media insert button")` with 2 tests |
| `packages/editor/src/lib/components/KBPage.svelte` | Pass `mediaItems` prop to `<MarkdownEditor>` |

---

### Task 1: Write failing tests for MarkdownEditor media picker

**Files:**
- Modify: `packages/editor/test/MarkdownEditor.test.ts`

- [ ] **Step 1: Append the failing `describe` block to `MarkdownEditor.test.ts`**

Add this import at the top of the file (after the existing imports):

```typescript
import type { MediaItem } from "../src/lib/components/ui/mediaTypes";
```

Then append the entire `describe` block below the existing tests:

```typescript
describe("MarkdownEditor — media picker", () => {
  const imgItem: MediaItem = {
    id: "photo.jpg",
    name: "photo.jpg",
    url: "/api/kb/e1/attachments/photo.jpg",
    thumbnailUrl: "/api/kb/e1/attachments/photo.jpg",
    type: "image",
  };
  const pdfItem: MediaItem = {
    id: "doc.pdf",
    name: "doc.pdf",
    url: "/api/kb/e1/attachments/doc.pdf",
    thumbnailUrl: "/api/kb/e1/attachments/doc.pdf.thumb.jpg",
    type: "document",
  };

  it("does not show 📷 button when mediaItems prop is omitted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true } });
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).toBeNull();
    unmount(app);
    target.remove();
  });

  it("does not show 📷 button when mediaItems is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [] },
    });
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).toBeNull();
    unmount(app);
    target.remove();
  });

  it("shows 📷 button when mediaItems are provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking 📷 button opens picker panel", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    expect(target.querySelector(".media-picker")).toBeNull();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector(".media-picker")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking image tile inserts ![name](url) and closes picker", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".media-tile") as HTMLButtonElement).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("![photo.jpg](/api/kb/e1/attachments/photo.jpg)");
    expect(target.querySelector(".media-picker")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking PDF tile inserts clickable thumbnail markdown and closes picker", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [pdfItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelector(".media-tile") as HTMLButtonElement).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe(
      "[![doc.pdf](/api/kb/e1/attachments/doc.pdf.thumb.jpg)](/api/kb/e1/attachments/doc.pdf)",
    );
    expect(target.querySelector(".media-picker")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("pressing Escape closes picker without inserting", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector(".media-picker")).not.toBeNull();
    target.querySelector(".tb-media-wrap")!.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
    flushSync();
    expect(target.querySelector(".media-picker")).toBeNull();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    unmount(app);
    target.remove();
  });

  it("clicking outside the picker closes it without inserting", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector(".media-picker")).not.toBeNull();
    document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(target.querySelector(".media-picker")).toBeNull();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/MarkdownEditor.test.ts 2>&1 | tail -30
```

Expected: 8 new tests FAIL — the `mediaItems` prop, picker button, and `.media-tile` class don't exist yet.

---

### Task 2: Implement the media picker in MarkdownEditor

**Files:**
- Modify: `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`

- [ ] **Step 3: Update the `<script>` block**

Replace the entire `<script lang="ts">` block with:

```svelte
<script lang="ts">
  import { marked } from "marked";
  import DOMPurify from "dompurify";
  import type { MediaItem } from "./mediaTypes";

  marked.use({ breaks: true, gfm: true });

  interface Props {
    value: string;
    editing: boolean;
    placeholder?: string;
    minHeight?: string;
    mediaItems?: MediaItem[];
  }

  let {
    value = $bindable(),
    editing = $bindable(),
    placeholder = "Click to add markdown content…",
    minHeight = "200px",
    mediaItems = [],
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

  const renderedHtml = $derived(
    value.trim() ? DOMPurify.sanitize(marked(value) as string) : "",
  );

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

  function linePrefix(prefix: string) {
    if (!textareaEl) return;
    const s = textareaEl.selectionStart;
    const lineStart = value.lastIndexOf("\n", s - 1) + 1;
    value = value.slice(0, lineStart) + prefix + value.slice(lineStart);
    const ns = lineStart + prefix.length;
    setTimeout(() => { if (textareaEl) { textareaEl.focus(); textareaEl.setSelectionRange(ns, ns); } }, 0);
  }

  function insertMedia(item: MediaItem): void {
    const md =
      item.type === "document"
        ? `[![${item.name}](${item.thumbnailUrl})](${item.url})`
        : `![${item.name}](${item.url})`;
    insert(md);
    pickerOpen = false;
  }
</script>
```

- [ ] **Step 4: Update the toolbar template**

Replace the `{#if editing}` block's toolbar div with this updated version (keep the textarea and `{:else}` block unchanged):

```svelte
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
              <button
                class="media-tile"
                type="button"
                title={item.name}
                onclick={() => insertMedia(item)}
              >
                <img src={item.thumbnailUrl} alt={item.name} />
                <span class="media-tile-name">{item.name}</span>
              </button>
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
```

- [ ] **Step 5: Add CSS for the picker**

In the `<style>` block, add these rules after `.tb-sep { ... }`:

```css
  .tb-media-wrap { position: relative; display: inline-block; }
  .media-picker {
    position: absolute; top: calc(100% + 4px); left: 0; z-index: 100;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: var(--space-2);
    display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2);
    max-height: 180px; overflow-y: auto; min-width: 160px;
  }
  .media-tile {
    background: none; border: 1px solid var(--border); border-radius: var(--radius-sm);
    cursor: pointer; padding: 4px;
    display: flex; flex-direction: column; align-items: center; gap: 2px;
  }
  .media-tile:hover { background: var(--surface-hover); border-color: var(--accent); }
  .media-tile img {
    width: 40px; height: 40px; object-fit: cover;
    border-radius: var(--radius-sm); display: block;
  }
  .media-tile-name {
    font-size: 10px; color: var(--text-muted);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    max-width: 60px; text-align: center;
  }
```

- [ ] **Step 6: Run MarkdownEditor tests — all 23 should pass**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/MarkdownEditor.test.ts 2>&1 | tail -20
```

Expected: 23 tests pass (15 existing + 8 new).

---

### Task 3: Wire mediaItems in KBPage and add tests

**Files:**
- Modify: `packages/editor/test/KBPage.test.ts`
- Modify: `packages/editor/src/lib/components/KBPage.svelte`

- [ ] **Step 7: Append failing KBPage tests**

Add this block to the end of `packages/editor/test/KBPage.test.ts`:

```typescript
describe("KBPage — media insert button", () => {
  it("shows 📷 button when entry has attachments and Content tab is in edit mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ attachments: ["photo.jpg"] });
    const store = makeStore([entry]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("does not show 📷 button when entry has no attachments", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const entry = makeEntry({ attachments: [] });
    const store = makeStore([entry]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).toBeNull();
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 8: Run KBPage tests to confirm 2 new tests fail**

```bash
cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts 2>&1 | tail -20
```

Expected: 2 new tests FAIL — the `mediaItems` prop is not yet passed to `<MarkdownEditor>` in `KBPage.svelte`.

- [ ] **Step 9: Wire mediaItems prop in KBPage.svelte**

In `packages/editor/src/lib/components/KBPage.svelte`, find the `<MarkdownEditor>` block (around line 189) and replace it:

```svelte
          <MarkdownEditor
            bind:value={draftContent}
            bind:editing
            placeholder="Start writing in Markdown…"
          />
```

Replace with:

```svelte
          <MarkdownEditor
            bind:value={draftContent}
            bind:editing
            mediaItems={contentTab === "content" ? mediaItems : []}
            placeholder="Start writing in Markdown…"
          />
```

- [ ] **Step 10: Run full test suite — all tests should pass**

```bash
cd /projects/myhome/packages/editor && npx vitest run 2>&1 | tail -20
```

Expected: All tests pass. Look for a summary like `X tests passed` with no failures.

- [ ] **Step 11: Commit**

```bash
cd /projects/myhome && git add packages/editor/test/MarkdownEditor.test.ts packages/editor/src/lib/components/ui/MarkdownEditor.svelte packages/editor/test/KBPage.test.ts packages/editor/src/lib/components/KBPage.svelte docs/superpowers/plans/2026-07-01-kb-inline-media-insert.md
git commit -m "feat(kb): inline media insert — 📷 toolbar picker inserts images and PDFs at cursor"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Covered by |
|-----------------|-----------|
| `mediaItems?: MediaItem[]` prop on MarkdownEditor | Task 2 script block |
| 📷 button hidden when `mediaItems` empty | Tests + `{#if mediaItems.length > 0}` in toolbar |
| 📷 button visible when `mediaItems` non-empty | Tests + same guard |
| Click 📷 → picker panel opens | Test step 4 + `pickerOpen = !pickerOpen` handler |
| Image tile → `![name](url)` inserted | Test step 5 + `insertMedia` for `type === "image"` |
| PDF tile → `[![name](thumbUrl)](url)` inserted | Test step 6 + `insertMedia` for `type === "document"` |
| Picker closes after tile click | Asserted in both insert tests |
| Escape key → picker closes | Test step 7 + `onkeydown` on `.tb-media-wrap` |
| Click outside → picker closes | Test step 8 + `$effect` with `document.addEventListener` |
| KBPage passes `mediaItems` to editor | Task 3 |
| Passing `[]` on Media tab hides button | `contentTab === "content" ? mediaItems : []` in KBPage |
| No backend changes | Confirmed — all attachment URLs come from existing `mediaItems` derived state |

**Placeholder scan:** No TBD, TODO, or incomplete sections — every step has full code.

**Type consistency:** `MediaItem` imported from `./mediaTypes` in both `MarkdownEditor.svelte` (new) and `KBPage.svelte` (already present). `insertMedia(item: MediaItem)` uses `item.type`, `item.name`, `item.url`, `item.thumbnailUrl` — all defined on `MediaItem`. The `wrapEl` ref is `HTMLElement | null` matching `bind:this` on a `<div>`.
