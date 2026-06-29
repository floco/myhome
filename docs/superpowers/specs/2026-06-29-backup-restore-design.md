# Backup & Restore — Design Spec

**Date:** 2026-06-29
**Feature:** Full data backup to zip and restore from zip, surfaced in the Settings module.

---

## Overview

Users can download a complete backup of all application data as a `.zip` file, and restore from a previously downloaded backup. The feature lives in the Settings page as a dedicated card.

---

## Data Scope

All contents of `DATA_DIR` (default `/data/`) are included in the backup:

| Path | Content |
|---|---|
| `house.json` | Floor plan |
| `chores.json` | Chore tracker |
| `costs.json` | Costs |
| `inventory.json` | Inventory items |
| `inventory-attachments/<id>/` | Inventory binary attachments |
| `kb/*.md` | Knowledge base articles |
| `settings.json` | Categories and suppliers |
| `works.json` | Works |
| `works-attachments/<id>/` | Works binary attachments |

---

## Architecture

### Backend — `routes/backup.py`

Two new endpoints registered in `main.py`:

**`GET /api/backup/download`**
- Walks `DATA_DIR` recursively using `zipfile.ZipFile`.
- Builds the zip in memory (`io.BytesIO`).
- Returns a `StreamingResponse` with:
  - `Content-Type: application/zip`
  - `Content-Disposition: attachment; filename="myhome-backup-YYYY-MM-DD.zip"` (today's date)
- Returns 500 if `DATA_DIR` is unreadable.

**`POST /api/backup/restore`**
- Accepts a multipart `UploadFile`.
- Validates the upload is a readable zip (`zipfile.is_zipfile`); returns 400 with `{"detail": "Invalid backup file"}` if not.
- Clears all contents of `DATA_DIR` (files and subdirectories, but not `DATA_DIR` itself).
- Extracts the zip into `DATA_DIR`.
- Returns 204 on success.
- Note: if extraction fails mid-way, `DATA_DIR` may be in a partial state (no rollback in v1).

### Frontend — `SettingsPage.svelte`

A new "Backup & Restore" card added at the bottom of the settings page.

**Download Backup button**
- Calls `GET /api/backup/download` via `fetch`.
- Receives the response as a blob, creates a temporary `<a>` element with an object URL, and triggers a browser download.
- Shows a spinner while in-flight.
- Shows an inline error message on failure.

**Restore from Backup button**
- Triggers a hidden `<input type="file" accept=".zip">` click.
- On file selection, opens a confirmation modal (reuses the existing shared `Modal` component) with the message: *"This will replace all current data with the contents of the backup. This cannot be undone."*
- Cancel dismisses the modal; Restore posts the file as `multipart/form-data` to `POST /api/backup/restore`.
- Shows an inline success message on 204, an inline error message on any other response.
- Resets the file input after each attempt so the user can immediately try again.

---

## Error Handling

| Scenario | Backend | Frontend |
|---|---|---|
| DATA_DIR unreadable on download | 500 | "Backup failed. Please try again." |
| Uploaded file is not a zip | 400 `{"detail": "Invalid backup file"}` | "Invalid backup file." |
| Extraction fails mid-way | 500 | "Restore failed. Data may be in a partial state." |
| Network error | — | Generic "Something went wrong." |

---

## Testing

**Backend (`tests/test_backup.py`)**
- `GET /api/backup/download` returns a valid zip containing the expected files from a test DATA_DIR.
- `POST /api/backup/restore` with a valid zip replaces DATA_DIR contents correctly.
- `POST /api/backup/restore` with a non-zip file returns 400.

**Frontend (Vitest)**
- The download button calls the correct endpoint and triggers a download.
- Selecting a file shows the confirmation modal.
- Confirming posts the file to the restore endpoint.
- Cancelling dismisses without posting.
- Success and error states render the correct inline messages.
