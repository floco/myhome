# Works Media Gallery — Design Document

**Status:** Approved for planning
**Date:** 2026-06-29

## Overview

Add multi-image upload and a media gallery to the Works module. The existing "Attachments" tab (PDF-only, list view) is replaced by a "Media" tab that handles both images and PDFs in a grid or list view. Clicking any item opens a fullscreen lightbox. PDF thumbnails are generated server-side on upload. The two new UI components (`MediaGallery`, `Lightbox`) are fully generic and reusable in other modules (e.g. KB).

---

## Data Model

No changes to `works.json` or the `Work` model. `attachments: list[str]` continues to store filenames for all media (images and PDFs alike). Type is inferred from the file extension at render time.

PDF thumbnails are stored as `{filename}.thumb.jpg` in the same per-work directory (`/data/works-attachments/{workId}/`). They are derived files — not listed in `attachments` and not deletable independently. They are deleted alongside the parent PDF when the parent attachment is deleted.

---

## Backend

### File acceptance

Remove the PDF-only guard in `POST /api/works/{id}/attachments`. Accepted types:

| Type | Content-types | Extensions |
|------|--------------|------------|
| Image | `image/jpeg`, `image/png`, `image/webp` | `.jpg`, `.jpeg`, `.png`, `.webp` |
| PDF | `application/pdf`, `application/octet-stream` | `.pdf` |

Reject everything else with HTTP 400.

### Filename sanitisation

`_sanitise_filename` is updated to preserve the original file extension (drop the forced `.pdf` append). Sanitisation rules remain: spaces → underscores, characters outside `[a-zA-Z0-9._-]` stripped.

### PDF thumbnail generation

On PDF upload, after saving the file, render page 1 as a JPEG using `pymupdf` (pure Python, no system binary required). Store as `{sanitised_filename}.thumb.jpg` in the same directory. If thumbnail generation fails (e.g. corrupt PDF), log a warning and continue — the upload still succeeds.

```python
import fitz  # pymupdf

def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    mat = fitz.Matrix(1.5, 1.5)   # ~108 dpi
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(thumb_path))
```

### Content-type serving

`GET /api/works/{id}/attachments/{filename}` switches from hardcoded `application/pdf` to `mimetypes.guess_type(filename)`, falling back to `application/octet-stream`.

### Thumbnail deletion

`delete_attachment` is updated: when deleting a PDF, also delete `{filename}.thumb.jpg` if it exists.

### No new routes

Thumbnails are served by the existing GET route. No new endpoints.

---

## Frontend

### `MediaItem` interface

Defined alongside the shared components in `lib/components/ui/`:

```ts
export interface MediaItem {
  id: string;           // unique key; passed to onDelete callback
  name: string;         // display filename
  url: string;          // view/download URL (list view link, lightbox "Open" button)
  thumbnailUrl: string; // URL for grid thumbnail
  type: "image" | "document";
  // "image"    → lightbox shows full image
  // "document" → lightbox shows thumbnail + "Open ↗" button
}
```

### `MediaGallery.svelte` (`lib/components/ui/`)

Generic component. Props:

```ts
interface Props {
  items: MediaItem[];
  accept?: string;               // file input accept attr; default "image/*,.pdf"
  uploading?: boolean;
  uploadError?: string | null;
  onUpload: (files: File[]) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}
```

**Behaviour:**

- Header row: item count label (left) + grid/list icon toggle buttons (right).
- **Grid view** (default): responsive `flex-wrap` of fixed-size tiles (e.g. 120×100px).
  - Images: `<img src={thumbnailUrl}>` fills the tile.
  - Documents: `<img src={thumbnailUrl}>` + small "PDF" badge in the top-right corner.
  - Hover: dim + show delete ✕ button overlay.
  - Click tile (not ✕): open lightbox at that index.
- **List view**: one row per item — icon + `name` (clickable, opens lightbox) + delete ✕ button. Same appearance as the current Attachments tab. There is no direct `target="_blank"` link; the lightbox "Open ↗" button handles that for documents.
- **Drag-and-drop**: the full component area is a drop target. `dragover` adds a highlighted border. `drop` extracts `event.dataTransfer.files` and calls `onUpload`.
- **Upload button**: `<label>` wrapping a hidden `<input type="file" multiple accept={accept}>`. On change, calls `onUpload(Array.from(files))`.
- `onUpload` is called with all selected/dropped files at once; the parent is responsible for uploading them (sequentially or in parallel — its choice).
- `uploading` prop disables the upload button and shows "Uploading…".
- `uploadError` prop shows an error line below the upload button.
- Empty state: centred text "No media yet." with a dashed border drop zone.
- Thumbnail fallback: if `thumbnailUrl` returns a 404 (e.g. PDF thumbnail generation failed), the tile shows a generic document icon via `<img onerror>` replacement.

### `Lightbox.svelte` (`lib/components/ui/`)

Generic component. Props:

```ts
interface Props {
  items: MediaItem[];
  initialIndex: number;
  onclose: () => void;
}
```

**Behaviour:**

- `position: fixed; inset: 0` dark overlay (`rgba(0,0,0,0.88)`), `z-index` above modal.
- Centre-displays the current item:
  - `type === "image"`: `<img>` scaled to fit viewport with `max-width`/`max-height`.
  - `type === "document"`: thumbnail image + "Open PDF ↗" button that opens `url` in a new tab.
- Bottom bar: current filename + `{index+1} / {total}` counter.
- Left/right arrow buttons (hidden when at first/last item).
- Keyboard: `←` / `→` navigate, `Escape` closes.
- Click outside the content area closes the lightbox.

### `WorkModal.svelte` wiring

- Tab label: `"Attachments"` → `"Media"`. Count badge stays.
- In the Media tab body, replace the existing attachment markup with `<MediaGallery>`.
- `items` derived from `currentWork.attachments`:

```ts
const mediaItems = $derived(
  (currentWork?.attachments ?? []).map(name => {
    const url = `/api/works/${work!.id}/attachments/${name}`;
    const isPdf = name.toLowerCase().endsWith(".pdf");
    return {
      id: name,
      name,
      url,
      thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url,
      type: isPdf ? "document" : "image",
    } satisfies MediaItem;
  })
);
```

- `onUpload`: loops over files, calls `store.uploadAttachment(work.id, file)` for each sequentially. Sets `uploading` state and catches errors into `uploadError`.
- `onDelete`: calls `store.deleteAttachment(work.id, id)`.
- Lightbox state: `lightboxOpen: boolean` + `lightboxIndex: number` local to `WorkModal`.

---

## Reuse in KB module

The KB module wires `MediaGallery` with its own `items` mapping (different base URL) and its own upload/delete callbacks. `MediaGallery` and `Lightbox` require zero changes.

---

## Dependencies

| Package | Where | Notes |
|---------|-------|-------|
| `pymupdf` | backend | PDF thumbnail generation. Pure Python wheel, ~15 MB. Add to `pyproject.toml` / `requirements.txt`. |

No new frontend dependencies.

---

## Testing

**Backend:**
- `test_works.py`: upload JPEG/PNG → 201, verify filename in `attachments`. Upload unsupported type → 400. Upload PDF → thumbnail file created at `{filename}.thumb.jpg`. Delete PDF → thumbnail also deleted. GET attachment returns correct content-type for images.
- `test_works_persistence.py`: no changes needed.

**Frontend:**
- `MediaGallery.test.ts`: renders grid/list views, toggles between them, calls `onUpload` with files from drag-drop and input, calls `onDelete` on ✕ click, shows empty state.
- `Lightbox.test.ts`: renders current item, navigates with arrows and keyboard, calls `onclose` on ESC and outside click.
- `WorkModal.test.ts`: Media tab renders `MediaGallery`, attachment count badge reflects both images and PDFs.
