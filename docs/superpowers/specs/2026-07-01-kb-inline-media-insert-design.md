# KB Inline Media Insert — Design Spec

**Date:** 2026-07-01
**Status:** Approved

## Overview

Allow KB entry authors to insert uploaded attachments (images and PDFs) directly into markdown text while editing. A 📷 button appears in the MarkdownEditor toolbar when the entry has attachments. Clicking it opens a compact picker panel; selecting an item inserts the appropriate markdown at the cursor and closes the picker.

## Scope

Two files change:

- `packages/editor/src/lib/components/ui/MarkdownEditor.svelte` — add optional `mediaItems` prop, picker state, toolbar button, picker panel
- `packages/editor/src/lib/components/KBPage.svelte` — pass `mediaItems` to `<MarkdownEditor>`

No backend changes. All attachment URLs are already available in the derived `mediaItems` array.

## Data Flow

`KBPage` derives `mediaItems: MediaItem[]` from `selectedEntry.attachments`. This is passed as an optional prop to `MarkdownEditor` only when the content tab is active:

```svelte
<MarkdownEditor
  bind:value={draftContent}
  bind:editing
  mediaItems={contentTab === "content" ? mediaItems : []}
  placeholder="Start writing in Markdown…"
/>
```

Passing `[]` when on the Media tab keeps the picker button hidden.

## MarkdownEditor Changes

### New prop

```typescript
interface Props {
  value: string;
  editing: boolean;
  placeholder?: string;
  minHeight?: string;
  mediaItems?: MediaItem[];   // new — defaults to []
}
```

Import `MediaItem` from `./mediaTypes` (already used by `KBPage`).

### Toolbar button

A 📷 button is appended to the existing toolbar, rendered only when `mediaItems.length > 0`:

```svelte
{#if mediaItems.length > 0}
  <span class="tb-sep" aria-hidden="true"></span>
  <div class="tb-media-wrap">
    <button class="tb-btn" type="button" title="Insert media"
      onclick={() => { pickerOpen = !pickerOpen; }}>📷</button>
    {#if pickerOpen}
      <!-- picker panel -->
    {/if}
  </div>
{/if}
```

### Picker panel

Absolutely positioned below the 📷 button, inside the same `.tb-media-wrap` container (`position: relative`). The panel is a scrollable grid (max-height 180px, 2–3 columns) of tiles.

**Closing behaviour:**
- Item selected → insert + close
- Escape key (on the wrapping div) → close
- Click outside (the wrapping div loses focus via `onblur` with `relatedTarget` guard) → close

### Insertion format

| Type | Inserted markdown |
|------|------------------|
| Image (jpg, png, webp) | `![{name}]({url})` |
| PDF | `[![{name}]({thumbnailUrl})]({url})` |

For images, `thumbnailUrl === url`, so the rule simplifies to: images always use `url`, PDFs wrap the thumbnail image in a link to the PDF file.

Both cases use the existing `insert()` helper which places the text at the cursor and preserves selection.

### Picker tile

Each tile shows:
- The attachment thumbnail (`thumbnailUrl`) as a small image (40×40px, `object-fit: cover`)
- The filename truncated below

Clicking a tile:
1. Calls `insert(markdown)` with the correct format
2. Sets `pickerOpen = false`

### Local state added

```javascript
let pickerOpen = $state(false);
```

No state leaks to the parent.

## Insertion Helper Call

```javascript
function insertMedia(item: MediaItem): void {
  const md = item.type === "document"
    ? `[![${item.name}](${item.thumbnailUrl})](${item.url})`
    : `![${item.name}](${item.url})`;
  insert(md);
  pickerOpen = false;
}
```

## CSS

New classes scoped to MarkdownEditor:
- `.tb-media-wrap` — `position: relative; display: inline-block`
- `.media-picker` — absolute panel, `top: 100%`, `left: 0`, z-index above toolbar, border + shadow, scrollable, grid layout
- `.media-tile` — clickable tile, hover highlight
- `.media-tile img` — 40×40px, `object-fit: cover`, `border-radius: var(--radius-sm)`
- `.media-tile-name` — truncated filename, `font-size: 10px`, `color: var(--text-muted)`

## Testing

**MarkdownEditor tests (`MarkdownEditor.test.ts`):**
- No `mediaItems` prop → 📷 button absent
- Empty `mediaItems` → 📷 button absent
- Non-empty `mediaItems` → 📷 button present
- Click 📷 → picker panel appears
- Click image tile → inserts `![name](url)` at correct position, picker closes
- Click PDF tile → inserts `[![name](thumbUrl)](url)`, picker closes
- Escape key → closes picker without inserting
- Click outside → closes picker without inserting

**KBPage tests (`KBPage.test.ts`):**
- Entry with attachments + edit mode → 📷 button is present in toolbar
- Entry with no attachments + edit mode → 📷 button absent

## Non-Goals

- No multi-select insert
- No drag-and-drop from picker to text
- No upload-from-picker (upload stays in the Media tab)
- No change to how the preview renders inserted media (DOMPurify + marked handle it)
