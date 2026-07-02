# Multi-Module Media Gallery — Design Document

**Status:** Approved  
**Date:** 2026-06-29

## Overview

Extend the Works media gallery pattern (MediaGallery + Lightbox components, image + PDF upload, server-side PDF thumbnails) to four additional modules: Inventory, Costs/Finance, KB, and Chores.

---

## Modules in Scope

| Module | Current attachment support | UI surface | Change |
|--------|---------------------------|------------|--------|
| Inventory | `attachments: list[str]`, PDF-only backend routes, store methods, "Attachments" tab in modal | `InventoryModal` | Update backend to accept images + thumbnails; rename tab → "Media"; replace list with MediaGallery |
| Costs | None | `CostsEntryModal` (no tabs) | Add model field, backend routes, store methods; add Info/Media tabs to modal |
| KB | None | 2-pane page (sidebar + content panel) | Add model field (`attachments` in `.md` frontmatter), backend routes, store methods; add Content/Media tab toggle in content panel |
| Chores | None | Inline edit in `ChoresPage` | Add model field, backend routes, store methods; introduce `ChoreEditModal` with Info/Media tabs to replace inline edit |

---

## Backend Pattern (same for all modules)

### File acceptance
All modules accept: `.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`. Reject all others → HTTP 400.

### Filename sanitisation
`_sanitise_filename`: spaces → underscores, strip non-`[a-zA-Z0-9._-]` chars, preserve original extension.

### PDF thumbnail
After PDF upload: generate `{filename}.thumb.jpg` via `pymupdf` (already installed). Failures are logged and silently ignored (upload still succeeds).

### Serving
`GET .../attachments/{filename}` → `mimetypes.guess_type(filename)`, fallback `application/octet-stream`.

### Deletion
`delete_attachment` removes the file and any `.thumb.jpg` sibling. Entity deletion removes the whole attachment directory.

### URL patterns
- Inventory: `/api/inventory/items/{id}/attachments/{filename}` (existing, updated)
- Costs: `/api/costs/entries/{id}/attachments/{filename}` (new)
- KB: `/api/kb/{id}/attachments/{filename}` (new)
- Chores: `/api/chores/{id}/attachments/{filename}` (new)

---

## KB: Frontmatter Format

`KBEntry` stores entries as `.md` files with YAML-style frontmatter. `attachments` is serialised as a comma-separated string on a single line:

```
---
id: ...
title: ...
createdAt: ...
updatedAt: ...
attachments: photo.jpg,invoice.pdf
---
```

The line is omitted when the list is empty (backward-compatible). The parser splits on `,` and filters empty strings.

---

## Frontend Pattern (per module)

### Store additions (Costs, KB, Chores)
```typescript
async function uploadAttachment(id: string, file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`/api/{module}/{id}/attachments`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const result = await resp.json();
  await init();
  return result.filename as string;
}

async function deleteAttachment(id: string, filename: string): Promise<void> {
  const resp = await fetch(`/api/{module}/{id}/attachments/${filename}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  await init();
}
```

### MediaItem mapping
```typescript
const mediaItems = $derived<MediaItem[]>(
  (currentEntity?.attachments ?? []).map(name => {
    const url = `/api/{module}/{id}/attachments/${name}`;
    const isPdf = name.toLowerCase().endsWith(".pdf");
    return { id: name, name, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
  })
);
```

### Lightbox state
```typescript
let lightboxOpen = $state(false);
let lightboxIndex = $state(0);
function handleItemClick(index: number): void { lightboxIndex = index; lightboxOpen = true; }
```

### Lightbox placement
Renders after the modal/component root: `{#if lightboxOpen}<Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />{/if}`

---

## Chores: ChoreEditModal

New `ChoreEditModal.svelte` replaces the inline edit form in `ChoresPage`. It is edit-only (creation stays in `NewChoreModal`). Info tab fields: name, emoji, frequency (freqN + freqUnit select), next due date, schedule-from-due checkbox. Media tab: `<MediaGallery>` + `<Lightbox>`.

`ChoresPage` drops its `editingId/editName/editEmoji/editPeriodDays/editNextDue/editScheduleFromDue` state and `startEdit/handleUpdate` functions. Replaces them with `editChore = $state<Chore | null>(null)` and `<ChoreEditModal>`.

---

## No new dependencies
`pymupdf` is already installed system-wide from the Works module.
