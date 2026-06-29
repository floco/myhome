# Works Media Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Works "Attachments" tab with a generic "Media" tab that supports images and PDFs in grid/list view with a fullscreen lightbox, server-side PDF thumbnails, drag-and-drop upload, and reusable `MediaGallery`/`Lightbox` components.

**Architecture:** Backend gains image acceptance + server-side PDF thumbnail generation (pymupdf) with no new routes. Two new generic Svelte UI components (`MediaGallery`, `Lightbox`) live in `lib/components/ui/` and are wired into `WorkModal` via callbacks, keeping the components store-agnostic.

**Tech Stack:** Python/FastAPI (backend), pymupdf (PDF thumbnails), Svelte 5 (frontend), Vitest + jsdom (tests)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `packages/backend/pyproject.toml` | Add pymupdf dependency |
| Modify | `packages/backend/src/myhome/persistence_works.py` | Sanitise filename, generate/delete PDF thumbnails |
| Modify | `packages/backend/src/myhome/routes/works.py` | File acceptance, content-type serving, call thumbnail generator |
| Modify | `packages/backend/tests/test_works.py` | Update + add tests for image upload, thumbnails |
| Create | `packages/editor/src/lib/components/ui/mediaTypes.ts` | `MediaItem` interface |
| Create | `packages/editor/src/lib/components/ui/MediaGallery.svelte` | Generic grid/list gallery with upload |
| Create | `packages/editor/src/lib/components/ui/Lightbox.svelte` | Generic fullscreen overlay with navigation |
| Create | `packages/editor/test/MediaGallery.test.ts` | MediaGallery unit tests |
| Create | `packages/editor/test/Lightbox.test.ts` | Lightbox unit tests |
| Modify | `packages/editor/src/lib/components/WorkModal.svelte` | Wire MediaGallery + Lightbox, rename tab |

---

## Task 1: Add pymupdf dependency

**Files:**
- Modify: `packages/backend/pyproject.toml`

- [ ] **Step 1: Add pymupdf to dependencies**

Edit `packages/backend/pyproject.toml` — add `"pymupdf>=1.24"` to the `dependencies` list:

```toml
[project]
name = "myhome-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.0",
    "uvicorn[standard]>=0.34",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
    "pymupdf>=1.24",
]
```

- [ ] **Step 2: Install and verify**

```bash
cd packages/backend
pip install -e ".[dev]"
python -c "import fitz; print(fitz.__version__)"
```

Expected: prints a version string like `1.24.x`.

- [ ] **Step 3: Commit**

```bash
git add packages/backend/pyproject.toml
git commit -m "chore: add pymupdf dependency for PDF thumbnail generation"
```

---

## Task 2: Backend — file acceptance, filename sanitisation, content-type serving

**Files:**
- Modify: `packages/backend/src/myhome/persistence_works.py`
- Modify: `packages/backend/src/myhome/routes/works.py`
- Modify: `packages/backend/tests/test_works.py`

### Background

The current `_sanitise_filename` forces a `.pdf` extension on every upload. The upload route rejects anything that isn't a PDF. The GET route hardcodes `application/pdf` as the content-type. All three need to change.

- [ ] **Step 1: Write failing tests**

Add these tests to `packages/backend/tests/test_works.py`. They reference functions that don't exist yet or behaviour that differs from the current code:

```python
def test_upload_image_jpeg_accepted(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.jpg"
    work = client.get("/api/works").json()["works"][0]
    assert "photo.jpg" in work["attachments"]


def test_upload_image_png_accepted(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("shot.png", b"\x89PNG\r\n" + b"\x00" * 100, "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "shot.png"


def test_upload_image_webp_accepted(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("photo.webp", b"RIFF" + b"\x00" * 100, "image/webp")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "photo.webp"


def test_upload_unsupported_type_rejected(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_sanitise_preserves_image_extension(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("my photo 2025.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_photo_2025.jpg"


def test_get_image_attachment_returns_correct_content_type(client, tmp_path):
    save_works(make_doc())
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("photo.png", b"\x89PNG\r\n" + b"\x00" * 100, "image/png")},
    )
    resp = client.get("/api/works/w1/attachments/photo.png")
    assert resp.status_code == 200
    assert "image/png" in resp.headers["content-type"]
```

Also update the existing `test_upload_non_pdf_rejected` test — it tests that `image/png` is rejected, which will no longer be true. Rename it to test a genuinely unsupported type instead:

```python
# REMOVE this test (it now contradicts desired behaviour):
# def test_upload_non_pdf_rejected(client, tmp_path): ...

# It is replaced by test_upload_unsupported_type_rejected above.
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/backend
pytest tests/test_works.py::test_upload_image_jpeg_accepted tests/test_works.py::test_upload_image_png_accepted tests/test_works.py::test_upload_unsupported_type_rejected tests/test_works.py::test_get_image_attachment_returns_correct_content_type -v
```

Expected: all FAIL.

- [ ] **Step 3: Update `_sanitise_filename` in `persistence_works.py`**

Replace the existing `_sanitise_filename` function in `packages/backend/src/myhome/routes/works.py`:

```python
def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"
```

The old version appended `.pdf` if the extension was missing — remove that logic entirely. A blank result falls back to `"attachment"`.

- [ ] **Step 4: Update the upload route in `routes/works.py`**

Replace the `upload_attachment` function body with the new acceptance logic:

```python
import os

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


@router.post("/api/works/{id}/attachments", status_code=201)
async def upload_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_works()
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(id, filename, data)
    if filename not in work.attachments:
        work.attachments.append(filename)
    save_works(doc)
    return {"filename": filename}
```

Add `import os` at the top of `routes/works.py` alongside the existing imports if it isn't there already.

- [ ] **Step 5: Update the GET attachment route to use `mimetypes`**

Replace the `get_attachment` function:

```python
import mimetypes

@router.get("/api/works/{id}/attachments/{filename}")
def get_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", filename=filename)
```

- [ ] **Step 6: Run the new tests — expect pass**

```bash
cd packages/backend
pytest tests/test_works.py::test_upload_image_jpeg_accepted tests/test_works.py::test_upload_image_png_accepted tests/test_works.py::test_upload_unsupported_type_rejected tests/test_works.py::test_get_image_attachment_returns_correct_content_type tests/test_works.py::test_sanitise_preserves_image_extension -v
```

Expected: all PASS.

- [ ] **Step 7: Run full backend test suite**

```bash
cd packages/backend
pytest -v
```

Expected: all pass. If `test_upload_non_pdf_rejected` still exists in the file, delete it now — it tests the old behaviour.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/routes/works.py packages/backend/tests/test_works.py
git commit -m "feat(backend): accept image uploads, fix filename sanitise, fix content-type serving"
```

---

## Task 3: Backend — PDF thumbnail generation and deletion

**Files:**
- Modify: `packages/backend/src/myhome/persistence_works.py`
- Modify: `packages/backend/src/myhome/routes/works.py`
- Modify: `packages/backend/tests/test_works.py`

### Background

When a PDF is uploaded, render page 1 as a JPEG thumbnail using `pymupdf` and store it as `{filename}.thumb.jpg` in the same directory. This derived file is NOT listed in `attachments`. When the PDF is deleted, the thumbnail is also deleted.

- [ ] **Step 1: Write failing tests**

Add to `packages/backend/tests/test_works.py`:

```python
def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def test_upload_pdf_creates_thumbnail(client, tmp_path):
    save_works(make_doc())
    pdf_bytes = _make_valid_pdf()
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "works-attachments" / "w1" / "invoice.pdf.thumb.jpg"
    assert thumb.exists(), "thumbnail should be created on PDF upload"


def test_upload_corrupt_pdf_still_succeeds(client, tmp_path):
    save_works(make_doc())
    resp = client.post(
        "/api/works/w1/attachments",
        files={"file": ("bad.pdf", b"%PDF corrupt garbage", "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "works-attachments" / "w1" / "bad.pdf.thumb.jpg"
    assert not thumb.exists(), "no thumbnail expected for corrupt PDF"


def test_delete_pdf_removes_thumbnail(client, tmp_path):
    save_works(make_doc())
    pdf_bytes = _make_valid_pdf()
    client.post(
        "/api/works/w1/attachments",
        files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
    )
    thumb = tmp_path / "works-attachments" / "w1" / "invoice.pdf.thumb.jpg"
    assert thumb.exists()
    client.delete("/api/works/w1/attachments/invoice.pdf")
    assert not thumb.exists(), "thumbnail should be removed when PDF is deleted"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/backend
pytest tests/test_works.py::test_upload_pdf_creates_thumbnail tests/test_works.py::test_upload_corrupt_pdf_still_succeeds tests/test_works.py::test_delete_pdf_removes_thumbnail -v
```

Expected: all FAIL.

- [ ] **Step 3: Add `generate_pdf_thumbnail` to `persistence_works.py`**

Add this function at the bottom of `packages/backend/src/myhome/persistence_works.py`:

```python
import logging

_log = logging.getLogger(__name__)


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz  # pymupdf
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)
```

- [ ] **Step 4: Call `generate_pdf_thumbnail` after PDF upload in `routes/works.py`**

In the `upload_attachment` function, after `save_attachment(id, filename, data)`, add:

```python
    save_attachment(id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(id, filename)
        thumb_path = pdf_path.parent / (filename + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in work.attachments:
        work.attachments.append(filename)
```

Also add `get_attachment_path` to the import from `..persistence_works` at the top of the file — it's already exported, just needs to be imported:

```python
from ..persistence_works import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    get_attachment_path,
    load_works,
    save_attachment,
    save_works,
)
```

- [ ] **Step 5: Update `delete_attachment` in `persistence_works.py` to also remove the thumbnail**

Replace the existing `delete_attachment` function:

```python
def delete_attachment(work_id: str, filename: str) -> bool:
    path = _attachments_dir(work_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True
```

- [ ] **Step 6: Run the new tests — expect pass**

```bash
cd packages/backend
pytest tests/test_works.py::test_upload_pdf_creates_thumbnail tests/test_works.py::test_upload_corrupt_pdf_still_succeeds tests/test_works.py::test_delete_pdf_removes_thumbnail -v
```

Expected: all PASS.

- [ ] **Step 7: Run full backend test suite**

```bash
cd packages/backend
pytest -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/persistence_works.py packages/backend/src/myhome/routes/works.py packages/backend/tests/test_works.py
git commit -m "feat(backend): generate PDF thumbnail on upload, clean up on delete"
```

---

## Task 4: Frontend — MediaItem interface

**Files:**
- Create: `packages/editor/src/lib/components/ui/mediaTypes.ts`

- [ ] **Step 1: Create the interface file**

Create `packages/editor/src/lib/components/ui/mediaTypes.ts`:

```typescript
export interface MediaItem {
  id: string;
  name: string;
  url: string;
  thumbnailUrl: string;
  type: "image" | "document";
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/editor/src/lib/components/ui/mediaTypes.ts
git commit -m "feat(ui): add MediaItem interface"
```

---

## Task 5: Frontend — MediaGallery component

**Files:**
- Create: `packages/editor/src/lib/components/ui/MediaGallery.svelte`
- Create: `packages/editor/test/MediaGallery.test.ts`

### Background

`MediaGallery` is a store-agnostic component. It receives a list of `MediaItem` objects and callbacks — it knows nothing about the API or any store. It supports grid view (default) and list view, drag-and-drop upload, and emits `onItemClick(index)` so the parent can open a lightbox.

- [ ] **Step 1: Write failing tests**

Create `packages/editor/test/MediaGallery.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount } from "svelte";
import MediaGallery from "../src/lib/components/ui/MediaGallery.svelte";
import type { MediaItem } from "../src/lib/components/ui/mediaTypes";

function makeItem(overrides: Partial<MediaItem> = {}): MediaItem {
  return {
    id: "photo.jpg",
    name: "photo.jpg",
    url: "/api/works/w1/attachments/photo.jpg",
    thumbnailUrl: "/api/works/w1/attachments/photo.jpg",
    type: "image",
    ...overrides,
  };
}

function setup(props: Record<string, unknown>) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(MediaGallery, { target, props });
  return { target, comp };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("MediaGallery — empty state", () => {
  it("shows empty state when no items", () => {
    const { target, comp } = setup({
      items: [],
      onUpload: vi.fn(),
      onDelete: vi.fn(),
      onItemClick: vi.fn(),
    });
    expect(target.textContent).toContain("No media yet");
    unmount(comp);
  });
});

describe("MediaGallery — grid view", () => {
  it("renders a tile per item in grid view", () => {
    const items = [makeItem({ id: "a.jpg", name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    expect(target.querySelectorAll(".media-tile").length).toBe(2);
    unmount(comp);
  });

  it("shows a PDF badge on document tiles", () => {
    const items = [makeItem({ id: "inv.pdf", name: "inv.pdf", type: "document" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    expect(target.querySelector(".pdf-badge")).not.toBeNull();
    unmount(comp);
  });

  it("calls onItemClick with the item index when tile is clicked", () => {
    const onItemClick = vi.fn();
    const items = [makeItem({ id: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick });
    (target.querySelectorAll(".media-tile")[1] as HTMLElement).click();
    expect(onItemClick).toHaveBeenCalledWith(1);
    unmount(comp);
  });

  it("calls onDelete with item id when delete button is clicked", () => {
    const onDelete = vi.fn();
    const items = [makeItem({ id: "photo.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete, onItemClick: vi.fn() });
    (target.querySelector(".tile-delete") as HTMLElement).click();
    expect(onDelete).toHaveBeenCalledWith("photo.jpg");
    unmount(comp);
  });
});

describe("MediaGallery — list view", () => {
  it("switches to list view when toggle is clicked", () => {
    const items = [makeItem()];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick: vi.fn() });
    (target.querySelector(".toggle-list") as HTMLElement).click();
    expect(target.querySelector(".media-list-row")).not.toBeNull();
    expect(target.querySelector(".media-tile")).toBeNull();
    unmount(comp);
  });

  it("calls onItemClick when list row name is clicked", () => {
    const onItemClick = vi.fn();
    const items = [makeItem({ id: "photo.jpg" })];
    const { target, comp } = setup({ items, onUpload: vi.fn(), onDelete: vi.fn(), onItemClick });
    (target.querySelector(".toggle-list") as HTMLElement).click();
    (target.querySelector(".list-name") as HTMLElement).click();
    expect(onItemClick).toHaveBeenCalledWith(0);
    unmount(comp);
  });
});

describe("MediaGallery — upload", () => {
  it("calls onUpload when files are selected via input", async () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const { target, comp } = setup({ items: [], onUpload, onDelete: vi.fn(), onItemClick: vi.fn() });
    const input = target.querySelector("input[type=file]") as HTMLInputElement;
    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    Object.defineProperty(input, "files", { value: [file], writable: false });
    input.dispatchEvent(new Event("change"));
    expect(onUpload).toHaveBeenCalledWith([file]);
    unmount(comp);
  });

  it("shows uploading state when uploading prop is true", () => {
    const { target, comp } = setup({
      items: [],
      uploading: true,
      onUpload: vi.fn(),
      onDelete: vi.fn(),
      onItemClick: vi.fn(),
    });
    expect(target.textContent).toContain("Uploading");
    unmount(comp);
  });

  it("shows upload error when uploadError prop is set", () => {
    const { target, comp } = setup({
      items: [],
      uploadError: "Upload failed",
      onUpload: vi.fn(),
      onDelete: vi.fn(),
      onItemClick: vi.fn(),
    });
    expect(target.textContent).toContain("Upload failed");
    unmount(comp);
  });

  it("calls onUpload when files are dropped", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const { target, comp } = setup({ items: [], onUpload, onDelete: vi.fn(), onItemClick: vi.fn() });
    const zone = target.querySelector(".drop-zone") as HTMLElement;
    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    const dt = { files: [file] };
    zone.dispatchEvent(Object.assign(new Event("drop"), { dataTransfer: dt }));
    expect(onUpload).toHaveBeenCalledWith([file]);
    unmount(comp);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/editor
npx vitest run test/MediaGallery.test.ts 2>&1 | tail -20
```

Expected: FAIL (component doesn't exist yet).

- [ ] **Step 3: Implement MediaGallery.svelte**

Create `packages/editor/src/lib/components/ui/MediaGallery.svelte`:

```svelte
<script lang="ts">
  import type { MediaItem } from "./mediaTypes";

  interface Props {
    items: MediaItem[];
    accept?: string;
    uploading?: boolean;
    uploadError?: string | null;
    onUpload: (files: File[]) => Promise<void>;
    onDelete: (id: string) => Promise<void>;
    onItemClick: (index: number) => void;
  }

  let {
    items,
    accept = "image/*,.pdf",
    uploading = false,
    uploadError = null,
    onUpload,
    onDelete,
    onItemClick,
  }: Props = $props();

  let viewMode = $state<"grid" | "list">("grid");
  let dragOver = $state(false);

  function handleFiles(files: FileList | File[]) {
    const arr = Array.from(files);
    if (arr.length) onUpload(arr);
  }

  function handleChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files) handleFiles(input.files);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragOver = false;
    if (e.dataTransfer?.files) handleFiles(e.dataTransfer.files);
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    dragOver = true;
  }

  function handleTileClick(e: MouseEvent, index: number) {
    onItemClick(index);
  }
</script>

<div
  class="drop-zone"
  class:drag-over={dragOver}
  ondrop={handleDrop}
  ondragover={handleDragOver}
  ondragleave={() => { dragOver = false; }}
>
  {#if items.length > 0}
    <div class="gallery-header">
      <span class="item-count">{items.length} item{items.length !== 1 ? "s" : ""}</span>
      <div class="view-toggles">
        <button class="toggle-grid" class:active={viewMode === "grid"} onclick={() => { viewMode = "grid"; }} title="Grid view">⊞</button>
        <button class="toggle-list" class:active={viewMode === "list"} onclick={() => { viewMode = "list"; }} title="List view">☰</button>
      </div>
    </div>
  {/if}

  {#if items.length === 0}
    <div class="empty-state">No media yet. Drop files here or use the button below.</div>
  {:else if viewMode === "grid"}
    <div class="media-grid">
      {#each items as item, i}
        <div class="media-tile" role="button" tabindex="0" onclick={(e) => handleTileClick(e, i)} onkeydown={(e) => { if (e.key === "Enter") onItemClick(i); }}>
          <img
            src={item.thumbnailUrl}
            alt={item.name}
            onerror={(e) => { (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 24 24'%3E%3Cpath fill='%23888' d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/%3E%3C/svg%3E"; }}
          />
          {#if item.type === "document"}
            <span class="pdf-badge">PDF</span>
          {/if}
          <button
            class="tile-delete"
            onclick={(e) => { e.stopPropagation(); onDelete(item.id); }}
            title="Delete"
          >✕</button>
        </div>
      {/each}
    </div>
  {:else}
    <div class="media-list">
      {#each items as item, i}
        <div class="media-list-row">
          <span class="list-icon">{item.type === "document" ? "📄" : "🖼"}</span>
          <button class="list-name" onclick={() => onItemClick(i)}>{item.name}</button>
          <button class="list-delete" onclick={() => onDelete(item.id)} title="Delete">✕</button>
        </div>
      {/each}
    </div>
  {/if}

  <div class="upload-row">
    <label class="upload-btn" class:uploading>
      {uploading ? "Uploading…" : "＋ Upload"}
      <input type="file" {accept} multiple style="display:none" onchange={handleChange} />
    </label>
    {#if uploadError}<div class="upload-error">{uploadError}</div>{/if}
  </div>
</div>

<style>
  .drop-zone {
    display: flex; flex-direction: column; gap: 8px;
    border: 2px solid transparent; border-radius: var(--radius-md);
    transition: border-color 0.15s;
    min-height: 120px;
  }
  .drop-zone.drag-over { border-color: var(--accent); background: var(--surface-alt); }

  .gallery-header { display: flex; align-items: center; justify-content: space-between; }
  .item-count { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; }
  .view-toggles { display: flex; gap: 2px; }
  .view-toggles button {
    background: none; border: 1px solid var(--border); color: var(--text-muted);
    padding: 2px 6px; border-radius: var(--radius-sm); cursor: pointer; font-size: 12px;
  }
  .view-toggles button.active { border-color: var(--accent); color: var(--accent); }

  .empty-state { font-size: 11px; color: var(--text-faint); text-align: center; padding: 20px 0; }

  .media-grid { display: flex; flex-wrap: wrap; gap: 8px; }
  .media-tile {
    position: relative; width: 120px; height: 100px;
    background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm);
    overflow: hidden; cursor: pointer; flex-shrink: 0;
  }
  .media-tile img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .media-tile:hover img { opacity: 0.7; }
  .pdf-badge {
    position: absolute; top: 4px; right: 4px;
    background: rgba(0,0,0,0.65); color: #fff; font-size: 8px;
    padding: 1px 4px; border-radius: 3px; letter-spacing: .04em;
  }
  .tile-delete {
    position: absolute; top: 2px; left: 2px; display: none;
    background: rgba(0,0,0,0.6); border: none; color: #fff;
    font-size: 10px; border-radius: 50%; width: 18px; height: 18px; cursor: pointer;
    align-items: center; justify-content: center; padding: 0;
  }
  .media-tile:hover .tile-delete { display: flex; }

  .media-list { display: flex; flex-direction: column; gap: 4px; }
  .media-list-row {
    display: flex; align-items: center; gap: 8px;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .list-icon { font-size: 14px; }
  .list-name {
    flex: 1; font-size: 11px; color: var(--accent); background: none; border: none;
    cursor: pointer; text-align: left; padding: 0; font-family: var(--font-sans);
  }
  .list-name:hover { text-decoration: underline; }
  .list-delete { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; }
  .list-delete:hover { color: var(--danger); }

  .upload-row { display: flex; flex-direction: column; gap: 4px; margin-top: 4px; }
  .upload-btn {
    background: var(--surface-alt); border: 1px dashed var(--border); color: var(--text-muted);
    padding: 7px 12px; border-radius: var(--radius-md); font-size: 11px; cursor: pointer;
    text-align: center; font-family: var(--font-sans); display: block;
  }
  .upload-btn:hover:not(.uploading) { background: var(--surface-hover); color: var(--text); }
  .upload-btn.uploading { color: var(--text-faint); cursor: default; }
  .upload-error { font-size: 10px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd packages/editor
npx vitest run test/MediaGallery.test.ts 2>&1 | tail -20
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/MediaGallery.svelte packages/editor/test/MediaGallery.test.ts
git commit -m "feat(ui): add generic MediaGallery component with grid/list toggle and drag-drop"
```

---

## Task 6: Frontend — Lightbox component

**Files:**
- Create: `packages/editor/src/lib/components/ui/Lightbox.svelte`
- Create: `packages/editor/test/Lightbox.test.ts`

### Background

`Lightbox` is a fullscreen overlay that cycles through `MediaItem[]`. Images are shown at full size; documents show their thumbnail + an "Open PDF ↗" button. It sits at `z-index: 200`, above the Modal (`z-index: 100`).

- [ ] **Step 1: Write failing tests**

Create `packages/editor/test/Lightbox.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount } from "svelte";
import Lightbox from "../src/lib/components/ui/Lightbox.svelte";
import type { MediaItem } from "../src/lib/components/ui/mediaTypes";

function makeItem(overrides: Partial<MediaItem> = {}): MediaItem {
  return {
    id: "photo.jpg",
    name: "photo.jpg",
    url: "/api/works/w1/attachments/photo.jpg",
    thumbnailUrl: "/api/works/w1/attachments/photo.jpg",
    type: "image",
    ...overrides,
  };
}

function setup(props: Record<string, unknown>) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(Lightbox, { target, props });
  return { target, comp };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("Lightbox — rendering", () => {
  it("renders the overlay", () => {
    const { target, comp } = setup({ items: [makeItem()], initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-overlay")).not.toBeNull();
    unmount(comp);
  });

  it("shows the filename and counter", () => {
    const items = [makeItem({ name: "photo.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("photo.jpg");
    expect(target.querySelector(".lightbox-counter")!.textContent).toContain("1 / 2");
    unmount(comp);
  });

  it("renders an img for image items", () => {
    const { target, comp } = setup({ items: [makeItem({ type: "image" })], initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-img")).not.toBeNull();
    unmount(comp);
  });

  it("renders a thumbnail and Open button for document items", () => {
    const item = makeItem({ type: "document", name: "invoice.pdf", url: "/api/works/w1/attachments/invoice.pdf" });
    const { target, comp } = setup({ items: [item], initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".lightbox-img")).not.toBeNull();
    const openBtn = target.querySelector(".lightbox-open-btn") as HTMLAnchorElement;
    expect(openBtn).not.toBeNull();
    expect(openBtn.href).toContain("invoice.pdf");
    unmount(comp);
  });
});

describe("Lightbox — navigation", () => {
  it("hides left arrow on first item", () => {
    const items = [makeItem(), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    expect(target.querySelector(".arrow-prev")).toBeNull();
    unmount(comp);
  });

  it("hides right arrow on last item", () => {
    const items = [makeItem(), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 1, onclose: vi.fn() });
    expect(target.querySelector(".arrow-next")).toBeNull();
    unmount(comp);
  });

  it("clicking right arrow advances to next item", () => {
    const items = [makeItem({ name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    (target.querySelector(".arrow-next") as HTMLElement).click();
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("b.jpg");
    unmount(comp);
  });

  it("clicking left arrow goes back to previous item", () => {
    const items = [makeItem({ name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 1, onclose: vi.fn() });
    (target.querySelector(".arrow-prev") as HTMLElement).click();
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("a.jpg");
    unmount(comp);
  });
});

describe("Lightbox — close", () => {
  it("calls onclose when clicking the backdrop", () => {
    const onclose = vi.fn();
    const { target, comp } = setup({ items: [makeItem()], initialIndex: 0, onclose });
    (target.querySelector(".lightbox-overlay") as HTMLElement).click();
    expect(onclose).toHaveBeenCalledOnce();
    unmount(comp);
  });

  it("calls onclose on Escape key", () => {
    const onclose = vi.fn();
    const { target, comp } = setup({ items: [makeItem()], initialIndex: 0, onclose });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(onclose).toHaveBeenCalledOnce();
    unmount(comp);
  });

  it("navigates with arrow keys", () => {
    const items = [makeItem({ name: "a.jpg" }), makeItem({ id: "b.jpg", name: "b.jpg" })];
    const { target, comp } = setup({ items, initialIndex: 0, onclose: vi.fn() });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
    expect(target.querySelector(".lightbox-name")!.textContent).toContain("b.jpg");
    unmount(comp);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/editor
npx vitest run test/Lightbox.test.ts 2>&1 | tail -20
```

Expected: all FAIL.

- [ ] **Step 3: Implement Lightbox.svelte**

Create `packages/editor/src/lib/components/ui/Lightbox.svelte`:

```svelte
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { MediaItem } from "./mediaTypes";

  interface Props {
    items: MediaItem[];
    initialIndex: number;
    onclose: () => void;
  }

  let { items, initialIndex, onclose }: Props = $props();

  let index = $state(initialIndex);
  const current = $derived(items[index]);

  function prev() { if (index > 0) index--; }
  function next() { if (index < items.length - 1) index++; }

  function handleKey(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
    else if (e.key === "ArrowLeft") prev();
    else if (e.key === "ArrowRight") next();
  }

  onMount(() => { document.addEventListener("keydown", handleKey); });
  onDestroy(() => { document.removeEventListener("keydown", handleKey); });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="lightbox-overlay" onclick={onclose}>
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="lightbox-content" onclick={(e) => e.stopPropagation()}>
    {#if index > 0}
      <button class="arrow-prev" onclick={prev}>‹</button>
    {/if}

    <div class="lightbox-media">
      <img
        class="lightbox-img"
        src={current.thumbnailUrl}
        alt={current.name}
        onerror={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
      />
      {#if current.type === "document"}
        <a
          class="lightbox-open-btn"
          href={current.url}
          target="_blank"
          rel="noopener"
          onclick={(e) => e.stopPropagation()}
        >Open PDF ↗</a>
      {/if}
    </div>

    {#if index < items.length - 1}
      <button class="arrow-next" onclick={next}>›</button>
    {/if}
  </div>

  <div class="lightbox-bar">
    <span class="lightbox-name">{current.name}</span>
    <span class="lightbox-counter">{index + 1} / {items.length}</span>
  </div>
</div>

<style>
  .lightbox-overlay {
    position: fixed; inset: 0; z-index: 200;
    background: rgba(0,0,0,0.88);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }
  .lightbox-content {
    position: relative; display: flex; align-items: center; justify-content: center;
    max-width: 90vw; max-height: 80vh;
  }
  .lightbox-media { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .lightbox-img { max-width: 80vw; max-height: 72vh; object-fit: contain; border-radius: var(--radius-md); }
  .lightbox-open-btn {
    background: var(--accent); color: #fff; padding: 8px 20px;
    border-radius: var(--radius-md); text-decoration: none; font-size: 13px;
    font-family: var(--font-sans);
  }
  .lightbox-open-btn:hover { opacity: 0.88; }
  .arrow-prev, .arrow-next {
    position: absolute; top: 50%; transform: translateY(-50%);
    background: rgba(0,0,0,0.5); border: none; color: #fff;
    font-size: 32px; width: 44px; height: 44px; border-radius: 50%;
    cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 1;
  }
  .arrow-prev { left: -56px; }
  .arrow-next { right: -56px; }
  .arrow-prev:hover, .arrow-next:hover { background: rgba(0,0,0,0.75); }
  .lightbox-bar {
    display: flex; gap: 16px; align-items: center; margin-top: 16px;
    color: rgba(255,255,255,0.7); font-size: 12px; font-family: var(--font-sans);
  }
  .lightbox-name { color: #fff; }
  .lightbox-counter { color: rgba(255,255,255,0.5); }
</style>
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd packages/editor
npx vitest run test/Lightbox.test.ts 2>&1 | tail -20
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/Lightbox.svelte packages/editor/test/Lightbox.test.ts
git commit -m "feat(ui): add generic Lightbox component with keyboard navigation"
```

---

## Task 7: Frontend — WorkModal wiring

**Files:**
- Modify: `packages/editor/src/lib/components/WorkModal.svelte`
- Create: `packages/editor/test/WorkModal.test.ts`

### Background

Replace the Attachments tab markup with `<MediaGallery>` and render `<Lightbox>` conditionally. Map `work.attachments` into `MediaItem[]`, constructing thumbnail URLs for PDFs. Upload iterates files sequentially. Tab label changes from "Attachments" to "Media".

- [ ] **Step 1: Write failing tests**

Create `packages/editor/test/WorkModal.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, tick } from "svelte";
import WorkModal from "../src/lib/components/WorkModal.svelte";

function makeStore(attachments: string[] = []) {
  return {
    works: [{ id: "w1", title: "Boiler repair", description: "", status: "done", categoryId: null, date: "2025-11-10", totalCost: 1200, supplierId: null, notes: "", attachments, placement: null }],
    loaded: true,
    loadError: null,
    createWork: vi.fn(),
    updateWork: vi.fn(),
    deleteWork: vi.fn(),
    uploadAttachment: vi.fn().mockResolvedValue("file.jpg"),
    deleteAttachment: vi.fn(),
    setPlacement: vi.fn(),
  };
}

function makeSettingsStore() {
  return { workCategories: [], suppliers: [] };
}

function setup(attachments: string[] = []) {
  const store = makeStore(attachments);
  const target = document.createElement("div");
  document.body.appendChild(target);
  const work = store.works[0] as NonNullable<(typeof store.works)[0]>;
  const comp = mount(WorkModal, {
    target,
    props: {
      work,
      store,
      settingsStore: makeSettingsStore(),
      onclose: vi.fn(),
    },
  });
  return { target, comp, store };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("WorkModal — Media tab", () => {
  it("has a Media tab (not Attachments)", () => {
    const { target, comp } = setup();
    const tabs = Array.from(target.querySelectorAll(".tab")).map((t) => t.textContent);
    expect(tabs.some((t) => t?.includes("Media"))).toBe(true);
    expect(tabs.some((t) => t?.includes("Attachments"))).toBe(false);
    unmount(comp);
  });

  it("shows MediaGallery when Media tab is active", async () => {
    const { target, comp } = setup(["photo.jpg"]);
    const mediaTab = Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media")) as HTMLElement;
    mediaTab.click();
    await tick();
    expect(target.querySelector(".drop-zone")).not.toBeNull();
    unmount(comp);
  });

  it("badge count includes both images and PDFs", () => {
    const { target, comp } = setup(["photo.jpg", "invoice.pdf"]);
    const mediaTab = Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media"));
    expect(mediaTab?.textContent).toContain("2");
    unmount(comp);
  });

  it("calls store.uploadAttachment for each uploaded file", async () => {
    const { target, comp, store } = setup();
    const mediaTab = Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Media")) as HTMLElement;
    mediaTab.click();
    await tick();
    const input = target.querySelector("input[type=file]") as HTMLInputElement;
    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    Object.defineProperty(input, "files", { value: [file], writable: false });
    input.dispatchEvent(new Event("change"));
    await tick();
    expect(store.uploadAttachment).toHaveBeenCalledWith("w1", file);
    unmount(comp);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/editor
npx vitest run test/WorkModal.test.ts 2>&1 | tail -20
```

Expected: FAIL (tab still says "Attachments", no `.drop-zone`).

- [ ] **Step 3: Update WorkModal.svelte**

Replace the entire content of `packages/editor/src/lib/components/WorkModal.svelte` with:

```svelte
<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    work: Work | null;
    store: WorksStore;
    settingsStore: SettingsStore;
    onclose: () => void;
    onplaceonmap?: (workId: string) => void;
  }

  let { work, store, settingsStore, onclose, onplaceonmap }: Props = $props();

  const isCreate = work === null;

  let activeTab = $state<"info" | "notes" | "media">("info");
  let title = $state(work?.title ?? "");
  let description = $state(work?.description ?? "");
  let status = $state<Work["status"]>(work?.status ?? "planned");
  let categoryId = $state(work?.categoryId ?? "");
  let date = $state(work?.date ?? new Date().toISOString().slice(0, 10));
  let totalCost = $state<string>(work?.totalCost != null ? String(work.totalCost) : "");
  let supplierId = $state(work?.supplierId ?? "");
  let notes = $state(work?.notes ?? "");

  let editingNotes = $state(isCreate);
  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);

  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  async function handleSave(): Promise<void> {
    if (!title.trim()) { error = "Title is required"; return; }
    if (!date) { error = "Date is required"; return; }
    saving = true; error = null;
    const patch = {
      title: title.trim(),
      description: description.trim(),
      status,
      categoryId: categoryId || null,
      date,
      totalCost: totalCost ? parseFloat(totalCost) || null : null,
      supplierId: supplierId || null,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createWork(patch);
        onclose();
      } else {
        await store.updateWork(work!.id, patch);
        editingNotes = false;
        onclose();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!work) return;
    deleting = true;
    try {
      await store.deleteWork(work.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!work) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) {
        await store.uploadAttachment(work.id, file);
      }
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Upload failed";
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!work) return;
    try {
      await store.deleteAttachment(work.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Delete failed";
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }

  const currentWork = $derived(
    work ? (store.works.find(w => w.id === work.id) ?? work) : null
  );
  const attachmentCount = $derived(currentWork?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentWork?.attachments ?? []).map(name => {
      const url = `/api/works/${work!.id}/attachments/${name}`;
      const isPdf = name.toLowerCase().endsWith(".pdf");
      return {
        id: name,
        name,
        url,
        thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url,
        type: isPdf ? "document" : "image",
      };
    })
  );
</script>

<Modal open={true} title={isCreate ? "＋ New work" : "Edit work"} {onclose} width="min(92vw, 820px)">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "info"} onclick={() => { activeTab = "info"; }}>Info</button>
    <button class="tab" class:active={activeTab === "notes"} onclick={() => { activeTab = "notes"; }}>Notes</button>
    <button
      class="tab"
      class:active={activeTab === "media"}
      disabled={isCreate}
      onclick={() => { activeTab = "media"; }}
    >Media{attachmentCount > 0 ? ` (${attachmentCount})` : ""}</button>
  </div>

  {#if activeTab === "info"}
    <div class="row">
      <label>Title *</label>
      <Input bind:value={title} placeholder="Work title" />
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Category</label>
        <select class="native-input" bind:value={categoryId}>
          <option value="">— None —</option>
          {#each settingsStore.workCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
      <div class="row">
        <label>Status</label>
        <select class="native-input" bind:value={status}>
          <option value="planned">Planned</option>
          <option value="in_progress">In progress</option>
          <option value="done">Done</option>
        </select>
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Date *</label>
        <DatePicker bind:value={date} />
      </div>
      <div class="row">
        <label>Total cost (€)</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={totalCost} placeholder="0.00" />
      </div>
    </div>
    <div class="row">
      <label>Supplier</label>
      <select class="native-input" bind:value={supplierId}>
        <option value="">— None —</option>
        {#each settingsStore.suppliers as s}
          <option value={s.id}>{s.name}</option>
        {/each}
      </select>
    </div>
    <div class="row">
      <label>Description</label>
      <textarea class="native-input desc-area" bind:value={description} placeholder="Short summary of the work…" rows="2"></textarea>
    </div>
  {:else if activeTab === "notes"}
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder="Click to add markdown notes…"
      minHeight="260px"
    />
    {#if editingNotes && !isCreate}
      <Button variant="secondary" onclick={() => { editingNotes = false; }}>Done editing</Button>
    {/if}
  {:else}
    <MediaGallery
      items={mediaItems}
      {uploading}
      {uploadError}
      onUpload={handleUpload}
      onDelete={handleDeleteAttachment}
      onItemClick={handleItemClick}
    />
  {/if}

  {#if error}<div class="modal-error">{error}</div>{/if}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ Confirm</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    {#if onplaceonmap && !isCreate}
      <Button variant="secondary" onclick={() => { onplaceonmap(work!.id); onclose(); }}>📍 Place on map</Button>
    {/if}
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? "Saving…" : isCreate ? "Create" : "Save"}
    </Button>
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab {
    padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans);
  }
  .tab:hover:not(:disabled) { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .tab:disabled { color: var(--text-faint); cursor: default; }

  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .desc-area { resize: vertical; min-height: 48px; }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run new WorkModal tests — expect pass**

```bash
cd packages/editor
npx vitest run test/WorkModal.test.ts 2>&1 | tail -20
```

Expected: all PASS.

- [ ] **Step 5: Run full frontend test suite**

```bash
cd packages/editor
npx vitest run 2>&1 | tail -20
```

Expected: all pass. If any pre-existing test references "Attachments" tab text by that exact name, update it to "Media".

- [ ] **Step 6: Run full backend test suite one final time**

```bash
cd packages/backend
pytest -v 2>&1 | tail -20
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/WorkModal.svelte packages/editor/test/WorkModal.test.ts
git commit -m "feat(works): wire MediaGallery + Lightbox into WorkModal, rename tab to Media"
```

---

## Done

All 7 tasks complete. The Works "Media" tab now supports:
- JPEG, PNG, WebP image uploads + existing PDF uploads
- Server-side PDF thumbnails generated on upload via `pymupdf`
- Grid view (default) and list view with toggle
- Drag-and-drop + multi-select file upload
- Fullscreen lightbox with keyboard navigation
- Reusable `MediaGallery` and `Lightbox` components ready for the KB module
