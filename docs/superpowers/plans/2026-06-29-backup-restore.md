# Backup & Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Backup & Restore card to the Settings page that lets users download all app data as a timestamped zip and restore from a previously downloaded backup.

**Architecture:** Two new FastAPI endpoints in `routes/backup.py` — one streams the entire DATA_DIR as a zip, the other accepts a zip upload and replaces DATA_DIR contents. The frontend adds a card to `SettingsPage.svelte` with a download button and a restore button that shows a confirmation modal before posting the file.

**Tech Stack:** Python `zipfile` + `io.BytesIO` + FastAPI `StreamingResponse` + `UploadFile`; Svelte 5 runes; existing shared `Modal`, `Button`, `Card` components; Vitest + jsdom for frontend tests; pytest + `TestClient` for backend tests.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `packages/backend/src/myhome/routes/backup.py` | Download and restore endpoints |
| Modify | `packages/backend/src/myhome/main.py` | Register backup router |
| Create | `packages/backend/tests/test_backup.py` | Backend tests for both endpoints |
| Modify | `packages/editor/src/lib/components/SettingsPage.svelte` | Add Backup & Restore card |
| Create | `packages/editor/test/SettingsPage.test.ts` | Frontend tests for backup card |

---

## Task 1: Backend — download endpoint

**Files:**
- Create: `packages/backend/src/myhome/routes/backup.py`
- Create: `packages/backend/tests/test_backup.py`
- Modify: `packages/backend/src/myhome/main.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_backup.py`:

```python
import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from myhome.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_download_backup_returns_zip_with_expected_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{"floors": []}')
    (tmp_path / "settings.json").write_text('{"version": 1}')
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "e1.md").write_text("# Article")

    resp = TestClient(app).get("/api/backup/download")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    cd = resp.headers["content-disposition"]
    assert "myhome-backup-" in cd
    assert ".zip" in cd

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "house.json" in names
    assert "settings.json" in names
    assert "kb/e1.md" in names


def test_download_backup_empty_data_dir(client):
    resp = client.get("/api/backup/download")
    assert resp.status_code == 200
    assert zipfile.ZipFile(io.BytesIO(resp.content)).namelist() == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /projects/myhome
python3 -m pytest packages/backend/tests/test_backup.py -v
```

Expected: FAIL — `404 Not Found` (route doesn't exist yet)

- [ ] **Step 3: Create the backup route with the download endpoint**

Create `packages/backend/src/myhome/routes/backup.py`:

```python
import io
import os
import shutil
import zipfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter()


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


@router.get("/api/backup/download")
def download_backup() -> StreamingResponse:
    data_dir = _data_dir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if data_dir.exists():
            for path in data_dir.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(data_dir))
    buf.seek(0)
    filename = f"myhome-backup-{date.today().isoformat()}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 4: Register the router in main.py**

Edit `packages/backend/src/myhome/main.py` — add the import and `include_router` call:

```python
import os
from pathlib import Path
from fastapi import FastAPI
from .routes import house, svg, ha, chores, inventory, settings, costs, works, kb, backup

app = FastAPI(title="MyHome Backend", version="0.1.0")
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)
app.include_router(chores.router)
app.include_router(inventory.router)
app.include_router(settings.router)
app.include_router(costs.router)
app.include_router(works.router)
app.include_router(kb.router)
app.include_router(backup.router)

# Serve built Svelte frontend (only present in production Docker image).
# Path is explicit so it works whether myhome is installed into site-packages or run from source.
_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
```

- [ ] **Step 5: Run the download tests to verify they pass**

```bash
python3 -m pytest packages/backend/tests/test_backup.py -v
```

Expected: `test_download_backup_returns_zip_with_expected_files` PASS, `test_download_backup_empty_data_dir` PASS

- [ ] **Step 6: Run the full backend suite to check for regressions**

```bash
python3 -m pytest packages/backend/tests/ -q
```

Expected: 168 passed (166 existing + 2 new)

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/routes/backup.py \
        packages/backend/src/myhome/main.py \
        packages/backend/tests/test_backup.py
git commit -m "feat(backup): add GET /api/backup/download endpoint"
```

---

## Task 2: Backend — restore endpoint

**Files:**
- Modify: `packages/backend/src/myhome/routes/backup.py`
- Modify: `packages/backend/tests/test_backup.py`

- [ ] **Step 1: Add the failing restore tests**

Append to `packages/backend/tests/test_backup.py`:

```python
def test_restore_replaces_data_dir_contents(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "old.json").write_text('{"old": true}')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("house.json", '{"floors": []}')
        zf.writestr("settings.json", '{"version": 1}')
    buf.seek(0)

    resp = TestClient(app).post(
        "/api/backup/restore",
        files={"file": ("backup.zip", buf.read(), "application/zip")},
    )

    assert resp.status_code == 204
    assert not (tmp_path / "old.json").exists()
    assert (tmp_path / "house.json").read_text() == '{"floors": []}'
    assert (tmp_path / "settings.json").read_text() == '{"version": 1}'


def test_restore_handles_subdirectories(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("kb/e1.md", "# Article")
        zf.writestr("inventory-attachments/i1/photo.jpg", b"fake-jpeg")
    buf.seek(0)

    resp = TestClient(app).post(
        "/api/backup/restore",
        files={"file": ("backup.zip", buf.read(), "application/zip")},
    )

    assert resp.status_code == 204
    assert (tmp_path / "kb" / "e1.md").read_text() == "# Article"
    assert (tmp_path / "inventory-attachments" / "i1" / "photo.jpg").exists()


def test_restore_rejects_non_zip(client):
    resp = client.post(
        "/api/backup/restore",
        files={"file": ("data.json", b'{"not": "a zip"}', "application/json")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid backup file"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest packages/backend/tests/test_backup.py::test_restore_replaces_data_dir_contents \
                  packages/backend/tests/test_backup.py::test_restore_handles_subdirectories \
                  packages/backend/tests/test_backup.py::test_restore_rejects_non_zip -v
```

Expected: FAIL — `404 Not Found` (restore route doesn't exist yet)

- [ ] **Step 3: Add the restore endpoint to backup.py**

Add to the bottom of `packages/backend/src/myhome/routes/backup.py` (after the download endpoint):

```python
@router.post("/api/backup/restore", status_code=204)
async def restore_backup(file: UploadFile) -> None:
    content = await file.read()
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise HTTPException(status_code=400, detail="Invalid backup file")
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    for child in data_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        zf.extractall(data_dir)
```

- [ ] **Step 4: Run all backup tests to verify they pass**

```bash
python3 -m pytest packages/backend/tests/test_backup.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Run the full backend suite to check for regressions**

```bash
python3 -m pytest packages/backend/tests/ -q
```

Expected: 171 passed

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/backup.py \
        packages/backend/tests/test_backup.py
git commit -m "feat(backup): add POST /api/backup/restore endpoint"
```

---

## Task 3: Frontend — Backup & Restore card

**Files:**
- Create: `packages/editor/test/SettingsPage.test.ts`
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`

- [ ] **Step 1: Write the failing frontend tests**

Create `packages/editor/test/SettingsPage.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsPage from "../src/lib/components/SettingsPage.svelte";

function makeStore() {
  return {
    costCategories: [],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
    loaded: true,
    loadError: null,
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    placeCostCategory: vi.fn(),
  };
}

describe("SettingsPage — Backup & Restore", () => {
  let target: HTMLDivElement;
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(new Blob(), { status: 200 })
    );
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:fake");
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    target.remove();
  });

  it("renders the Backup & Restore card with both buttons", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();
    expect(target.textContent).toContain("Backup & Restore");
    expect(target.textContent).toContain("Download Backup");
    expect(target.textContent).toContain("Restore from Backup");
    unmount(app);
  });

  it("has a hidden file input that accepts .zip files", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();
    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();
    expect(fileInput.accept).toBe(".zip");
    unmount(app);
  });

  it("calls GET /api/backup/download when Download Backup is clicked", async () => {
    fetchSpy.mockResolvedValue(
      new Response(new Blob(["fake-zip"]), {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="myhome-backup-2026-06-29.zip"' },
      })
    );
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const btn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.includes("Download Backup")
    )!;
    btn.click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchSpy).toHaveBeenCalledWith("/api/backup/download");
    unmount(app);
  });

  it("shows confirmation modal when a zip file is selected for restore", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change"));
    flushSync();

    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("This will replace all current data");
    unmount(app);
  });

  it("calls POST /api/backup/restore with FormData when Restore is confirmed", async () => {
    fetchSpy.mockResolvedValue(new Response(null, { status: 204 }));
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change"));
    flushSync();

    const restoreBtn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.trim() === "Restore"
    )!;
    restoreBtn.click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/backup/restore",
      expect.objectContaining({ method: "POST" })
    );
    unmount(app);
  });

  it("dismisses modal when Cancel is clicked without calling fetch", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change"));
    flushSync();

    const cancelBtn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.trim() === "Cancel"
    )!;
    cancelBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal")).toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /projects/myhome/packages/editor
npx vitest run test/SettingsPage.test.ts
```

Expected: FAIL — cannot find "Backup & Restore" in rendered output

- [ ] **Step 3: Add the Backup & Restore card to SettingsPage.svelte**

In `packages/editor/src/lib/components/SettingsPage.svelte`, make these changes:

**3a — Add `Modal` import** (line 7, after `import Card from "./ui/Card.svelte";`):

```svelte
  import Modal from "./ui/Modal.svelte";
```

**3b — Add backup state variables and functions** (add before the closing `</script>` tag, after the suppliers section):

```svelte
  // --- Backup & Restore ---
  let downloadingBackup = $state(false);
  let backupError = $state<string | null>(null);
  let restoreFile = $state<File | null>(null);
  let showRestoreConfirm = $state(false);
  let restoringBackup = $state(false);
  let restoreSuccess = $state(false);
  let restoreError = $state<string | null>(null);
  let fileInputEl: HTMLInputElement | undefined = $state();

  async function downloadBackup(): Promise<void> {
    downloadingBackup = true;
    backupError = null;
    restoreSuccess = false;
    try {
      const resp = await fetch("/api/backup/download");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const disposition = resp.headers.get("content-disposition") ?? "";
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match ? match[1] : "myhome-backup.zip";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      backupError = "Backup failed. Please try again.";
    } finally {
      downloadingBackup = false;
    }
  }

  function onFileSelected(e: Event): void {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    restoreFile = file;
    restoreError = null;
    restoreSuccess = false;
    showRestoreConfirm = true;
  }

  async function confirmRestore(): Promise<void> {
    if (!restoreFile) return;
    restoringBackup = true;
    restoreError = null;
    try {
      const form = new FormData();
      form.append("file", restoreFile);
      const resp = await fetch("/api/backup/restore", { method: "POST", body: form });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        const msg = (data as { detail?: string }).detail ?? `HTTP ${resp.status}`;
        throw new Error(msg);
      }
      restoreSuccess = true;
      showRestoreConfirm = false;
    } catch (e) {
      restoreError = e instanceof Error ? e.message : "Restore failed.";
    } finally {
      restoringBackup = false;
      restoreFile = null;
      if (fileInputEl) fileInputEl.value = "";
    }
  }

  function cancelRestore(): void {
    showRestoreConfirm = false;
    restoreFile = null;
    restoreError = null;
    if (fileInputEl) fileInputEl.value = "";
  }
```

**3c — Add Backup & Restore card and Modal**

In `SettingsPage.svelte`, find the exact block at the bottom of the template (the Suppliers card closing tag and the two closing divs — currently the last few lines before `<style>`):

```svelte
    </Card>

  </div>
</div>

<style>
```

Replace those lines with:

```svelte
    </Card>

    <!-- Backup & Restore -->
    <Card>
      <div class="section-header">
        <h2>Backup & Restore</h2>
      </div>
      <div class="backup-actions">
        <div class="backup-action">
          <p class="backup-desc">Download a zip archive of all your data.</p>
          <Button onclick={downloadBackup} disabled={downloadingBackup}>
            {downloadingBackup ? "Downloading…" : "Download Backup"}
          </Button>
        </div>
        <div class="backup-action">
          <p class="backup-desc">Replace all current data from a previously downloaded backup.</p>
          <Button variant="secondary" onclick={() => fileInputEl?.click()}>Restore from Backup</Button>
          <input
            bind:this={fileInputEl}
            type="file"
            accept=".zip"
            class="hidden-file-input"
            onchange={onFileSelected}
          />
        </div>
      </div>
      {#if backupError}<div class="error">{backupError}</div>{/if}
      {#if restoreError}<div class="error">{restoreError}</div>{/if}
      {#if restoreSuccess}<div class="success-msg">Restore complete. Reload the page to see updated data.</div>{/if}
    </Card>

  </div>
</div>

<Modal open={showRestoreConfirm} title="Restore Backup" onclose={cancelRestore} width="400px">
  {#snippet children()}
    <p class="restore-warning">This will replace all current data with the contents of the backup. This cannot be undone.</p>
  {/snippet}
  {#snippet footer()}
    <Button variant="secondary" onclick={cancelRestore}>Cancel</Button>
    <Button onclick={confirmRestore} disabled={restoringBackup}>
      {restoringBackup ? "Restoring…" : "Restore"}
    </Button>
  {/snippet}
</Modal>

<style>
```

**3d — Add backup styles** to the `<style>` block (after the `.error` rule):

```css
  .backup-actions { display: flex; flex-direction: column; gap: var(--space-4); }
  .backup-action { display: flex; flex-direction: column; gap: var(--space-2); }
  .backup-desc { margin: 0; font-size: 12px; color: var(--text-muted); }
  .hidden-file-input { display: none; }
  .success-msg { color: var(--success); font-size: 11px; margin-top: 6px; }
  .restore-warning { margin: 0; font-size: 13px; color: var(--text); line-height: 1.5; }
```

- [ ] **Step 4: Run the frontend tests to verify they pass**

```bash
cd /projects/myhome/packages/editor
npx vitest run test/SettingsPage.test.ts
```

Expected: 5 tests PASS

- [ ] **Step 5: Run the full frontend suite to check for regressions**

```bash
npx vitest run
```

Expected: 240 existing + 5 new = 245 tests passed across 36 test files

- [ ] **Step 6: Commit**

```bash
cd /projects/myhome
git add packages/editor/src/lib/components/SettingsPage.svelte \
        packages/editor/test/SettingsPage.test.ts
git commit -m "feat(backup): add Backup & Restore card to Settings page"
```
