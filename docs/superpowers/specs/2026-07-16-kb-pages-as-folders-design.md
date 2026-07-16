# KB module: pages as folders (Notion-style nesting), page icons, Trash

Date: 2026-07-16

## Summary

Replace the KB module's separate `kb_folders` data type (added 2026-07-14)
with a single unified concept: **pages can contain child pages**. A page
with children renders as an expandable node in the left tree — no
structural difference from any other page, it just has children. Folders
as a distinct thing go away entirely. Each page also gets a picker-driven
icon (default 📄 when unset), a live-updating link to a newly created child
page is inserted into the parent's content automatically, and deletion
becomes a cascading soft-delete with a Trash view (manual restore/purge,
no auto-expiry).

This supersedes [2026-07-14-kb-folders-design.md](2026-07-14-kb-folders-design.md)
(that plan's folder deletion-blocked/reparent-only/no-icon design is
replaced by everything below). No migration of existing folder data is
performed — existing folders are simply dropped; existing pages keep their
content and become top-level.

## Data model

KB pages remain markdown files on disk (`kb/<id>.md`, unchanged mechanism —
explicitly *not* moving to SQLite for this pass). `KBEntry` changes:

```python
class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""
    createdAt: str
    updatedAt: str
    attachments: list[str] = []
    parentId: str | None = None      # replaces folderId
    icon: str = "📄"                  # new
    order: int = 0                    # new — position among siblings
    deletedAt: str | None = None      # new — soft-delete marker, None = live
```

Each new field is persisted as its own frontmatter line, following the
existing pattern (`attachments`, formerly `folderId`).

`kb_folders` table, `persistence_kb_folders.py`, `KBFolder`/
`KBFolderCreate`/`KBFolderUpdate` models, folder REST routes, and folder
MCP tools are all deleted. A schema migration drops the `kb_folders` table.

**Migration of existing entries:** a one-time frontmatter rewrite (run from
`persistence_kb.py`, e.g. on first load after upgrade) adds `icon: "📄"`,
`deletedAt: null`, and `order` (assigned sequentially following the current
`createdAt` sort) to every existing entry file, and drops `folderId`
(entries that had one simply become top-level, `parentId: null`). No
attempt is made to reconstruct pages from the old `kb_folders` rows.

**Cycle prevention:** the existing `would_create_cycle` walk (previously
over `kb_folders`) is ported to walk `KBEntry.parentId` chains instead,
used both when moving a page (`parentId` change) and is checked server-side
on every `PUT`.

## Backend API (`routes/kb.py`)

- `GET /api/homes/{home_id}/kb` — returns `KBDocument{entries}` (no more
  `folders` key). Trashed entries (`deletedAt` set) are excluded.
- `POST /api/homes/{home_id}/kb` — accepts optional `parentId` and `icon`.
  When `parentId` is set: validates the parent exists and isn't trashed,
  assigns `order = max(sibling order) + 1`, and appends
  `\n\n[New page](#/kb/<newId>)\n` to the **parent's** content (see
  "Child-page links" below for why the bracketed text doesn't matter).
- `PUT /api/homes/{home_id}/kb/{id}` — accepts `title`/`content`/`parentId`/
  `icon`/`order`. A `parentId` or `order` change goes through cycle
  detection (can't move a page under its own descendant).
- `DELETE /api/homes/{home_id}/kb/{id}` — **soft delete**. Walks the
  subtree rooted at `id` and stamps `deletedAt = now()` on the page and
  every descendant. Returns `{ deletedCount: N }` so the UI can show
  "Page and N-1 sub-pages moved to Trash."
- `GET /api/homes/{home_id}/kb/trash` — flat list of entries with
  `deletedAt` set (not a tree — a trashed page's parent may itself be
  trashed or may not be, doesn't matter for this flat view).
- `POST /api/homes/{home_id}/kb/trash/{id}/restore` — clears `deletedAt` on
  `id` and on every currently-trashed descendant, restoring the whole
  deleted subtree at once. `parentId` is never rewritten by restore. If the
  restored page's own parent is still trashed (not part of this restore),
  the tree simply renders the restored page at the root level — see
  rendering rule below — until that parent is separately restored too.
- `DELETE /api/homes/{home_id}/kb/trash/{id}` — permanent delete of that
  one entry: removes the `.md` file and its `kb-attachments/<id>/` dir.
  Does **not** cascade to descendants (a permanently-deleted page's
  children, if still in trash, simply become orphaned trash entries the
  user can also permanently delete — acceptable since this is a rare
  cleanup action, not the common path).
- `POST /api/homes/{home_id}/kb/trash/empty` — permanently deletes every
  trashed entry for the home (file + attachments each).
- All `/kb/folders*` routes removed.

## MCP tools (`mcp_tools_kb.py`)

- `create_kb_entry` / `update_kb_entry` gain `parent_id` and `icon`
  parameters (replacing `folder_id`).
- `delete_kb_entry` becomes soft-delete (cascading), matching REST.
- New: `list_kb_trash`, `restore_kb_entry`, `permanently_delete_kb_entry`,
  `empty_kb_trash`.
- All `*_kb_folder` tools removed.

## Content: child-page links are live references, not frozen text

When a child page is created, a markdown link is inserted into the
parent's content: `[New page](#/kb/<childId>)` — appended at the end for
tree-driven creation, or at the cursor for the in-editor `/page` command
(see below). This is literal markdown text the user can freely cut, paste,
or move anywhere in the content; it is **not** required for the child to
appear in the tree (tree membership is driven purely by `parentId`,
independent of what's linked in content).

Critically, the bracketed link text is **not** the source of truth for
display. `MarkdownEditor`'s preview renderer special-cases any `href`
matching `#/kb/<id>`: at render time, it looks up that page's *current*
`title` and `icon` from `kbStore` and renders those instead of whatever
text is stored in the markdown. This means:

- Renaming a page automatically updates how it's displayed everywhere it's
  linked, with no cross-page content rewrite needed.
- If the linked page is deleted (including soft-deleted to Trash) or no
  longer exists, the link renders as a greyed-out, non-clickable
  "Page deleted" chip instead of a link.
- The raw markdown source is stable and simple (`[anything](#/kb/<id>)`);
  only the rendered label is computed live.

Clicking a `#/kb/<id>` link in rendered content navigates in-app (updates
`window.location.hash`) rather than triggering default anchor behavior.

## Routing

`App.svelte`'s hash router gains a per-page route: `#/kb/<id>` opens
`KBPage` with that page selected (extends the existing single `#/kb` hash,
which continues to work with no selection). This makes KB pages
bookmarkable/shareable and is what child-page links navigate to.

## Frontend: `KBTree.svelte`

Folders and entries collapse into one recursive concept. Each row:

- Disclosure triangle — shown only if the page has children; toggles
  expand/collapse only, does not change selection.
- `icon` (or default 📄), title.
- Hover reveals: "+" (add child page) and "⋯" menu (Rename, Add child page,
  Delete, Move to...).
- Clicking anywhere on the row (other than the triangle) opens that page's
  content — unlike the old folder rows, which had no content of their own.
- Sort order: by `order` field (ascending) — replaces the old
  folders-before-entries/alphabetical-vs-createdAt split. New pages append
  to the end of their sibling list.
- **Rendering rule:** a live page whose `parentId` points at a currently
  trashed page is rendered as if it were top-level (rather than vanishing
  from the tree). `parentId` itself is untouched — this is purely a
  display rule that resolves once the trashed ancestor is restored or
  permanently deleted.

**Toolbar:** the old separate "+ New" (entry) / "+ Folder" buttons collapse
into a single "+ New Page" (creates a top-level page).

**In-editor child creation:** `MarkdownEditor`, when used within KB, adds a
`/page` slash command that creates a new child page under the currently
open page and inserts its link at the cursor (same create+link flow as the
tree's "+" button, just positioned at the cursor rather than appended).

**Drag-and-drop:** extends today's reparent-only behavior to include
sibling reordering:
- Dropping onto a row nests the dragged page as its child (`parentId`
  update, appended to end of new siblings).
- Dropping between two rows reorders within the current parent (`order`
  update).
- Same cycle-detection guard as today (can't drop a page onto its own
  descendant), now checked against the page tree instead of folders.

**Trash:** a "Trash (N)" link at the bottom of the tree opens a flat list
view (title, deleted date, Restore / Delete Forever per row, "Empty Trash"
action for the whole list).

**Icon picker:** reuses the existing `EmojiPicker.svelte` component
unchanged (`bind:value={draft.icon}`), same pattern as Consumables/
Inventory/Chores/Settings categories. Default value `"📄"` means "no icon
selected" needs no special-case UI — it's just the stored default,
identical to how Consumables defaults to `"🛒"`.

## `kbStore.svelte.ts`

- Drops `folders` state and all `*Folder` methods.
- `entries` gains `icon`, `parentId`, `order` fields on the `KBEntry` type
  (removes `folderId`).
- `createEntry` accepts optional `parentId`/`icon`.
- `updateEntry`'s patch type gains `parentId?`, `icon?`, `order?`.
- `deleteEntry` return value/behavior changes to reflect soft-delete
  (still called the same way from the UI; the row disappears from
  `entries` because trashed rows are excluded from the `GET` response).
- New: `trash: KBEntry[]` state + `loadTrash()`, `restoreEntry(id)`,
  `permanentlyDeleteEntry(id)`, `emptyTrash()`.

## Testing

**Backend** (rewrite `test_kb.py`, delete `test_kb_folders.py`):
- Page CRUD with `parentId`/`icon`/`order`; cycle rejected on move (400).
- Delete cascades `deletedAt` to all descendants; response reports count.
- Trash list excludes live pages; restore cascades to trashed descendants;
  permanent delete removes file + attachments and does not cascade;
  empty-trash removes everything.
- Frontmatter round-trip for all new fields.
- Migration: existing entry with old `folderId` frontmatter loads with
  `parentId: null`, gets default `icon`/`order`/`deletedAt` on next save.

**MCP** (`test_mcp_tools_kb.py`): mirrors REST coverage above for the new/
changed tools; delete all `*_kb_folder` tool tests.

**Frontend**:
- `kbStore.test.ts`: rewritten for `parentId`/`icon`/`order`, trash methods.
- `KBTree.test.ts`: rewritten for unified page rows (icon rendering,
  conditional disclosure triangle, reorder + reparent drag-and-drop, cycle
  rejection, Trash link).
- New `KBTrash.test.ts` (or equivalent) for the trash list view.
- `MarkdownEditor` tests: `#/kb/<id>` link rendering resolves live
  title/icon, renders "Page deleted" chip for missing/trashed targets,
  `/page` slash command inserts a child link at cursor.
- `KBPage.test.ts`: updated for merged toolbar button, deep-link selection
  via `#/kb/<id>`.

**Edge cases:**
- Deleting a page with deeply nested descendants → all soft-deleted,
  correct count reported.
- Two pages linking to the same child → both show live-updated title on
  rename.
- Dragging a page into its own descendant → rejected (cycle guard).
- Restoring a page whose parent is still trashed → page (and its own
  trashed descendants) become live and render at the tree's root per the
  rendering rule above, until the former parent is separately restored.
- Existing entry with old `folderId` frontmatter → loads correctly as
  top-level page (migration path).

## Out of scope

- Auto-purge/retention policy for Trash (manual "Empty Trash" only).
- Cross-page backlinks ("pages that link here").
- Moving KB page storage from markdown files to SQLite.
- Any change to non-KB modules.
