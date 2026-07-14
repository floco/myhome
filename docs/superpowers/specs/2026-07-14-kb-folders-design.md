# KB module: card layout + folder tree view

Date: 2026-07-14

## Summary

Wrap the Knowledge Base page in a `Card` (matching the visual style already
used on Chores/Costs/etc.), and replace the flat entry list in the KB
sidebar with a hierarchical tree view that lets users organize entries into
folders and nested subfolders.

## Data model

### New entity: `KBFolder`

```python
class KBFolder(BaseModel):
    id: str
    name: str
    parentId: str | None = None
```

Folders are relational data (parent/child integrity, cycle prevention), so
they're stored in a new SQLite table `kb_folders`, following the existing
pattern of flat category tables (`inventory_categories`, `cost_categories`,
etc.) but with a self-referencing `parent_id` column to support nesting:

```
kb_folders: id, home_id, parent_id (FK -> kb_folders.id, nullable), name, order_index
```

KB entries themselves remain markdown files on disk (unchanged persistence
mechanism). `KBEntry` gains one new field:

```python
class KBEntry(BaseModel):
    ...
    folderId: str | None = None
```

persisted as a new frontmatter line (`folderId: xxx`), following the same
pattern as the existing `attachments` frontmatter field. Entries with no
`folderId` (all entries that exist today) render at the tree root —
no migration needed.

## Backend API

- `GET /api/homes/{home_id}/kb` — extended to return
  `{ version, entries, folders }` in one call, so the frontend builds the
  tree without a second round trip.
- `POST /api/homes/{home_id}/kb/folders` — create `{ name, parentId? }`
- `PUT /api/homes/{home_id}/kb/folders/{id}` — rename/move
  `{ name?, parentId? }`
- `DELETE /api/homes/{home_id}/kb/folders/{id}` — 400 if the folder has any
  entries or subfolders (deletion is blocked, never cascading)
- Existing `PUT /api/homes/{home_id}/kb/{id}` (update entry) accepts an
  optional `folderId` field — used to move an entry into/out of a folder.

Route paths don't collide with existing `/kb/{id}` routes: `/kb/folders`
and `/kb/folders/{id}` have different segment counts than `/kb/{id}`.

**Cycle prevention:** on folder move (`parentId` change), the server walks
up the new parent's ancestor chain and rejects (400) if the folder being
moved is the new parent itself or an ancestor of it.

## MCP tools

New tools alongside the existing `list/create/update/delete_kb_entry`:

- `list_kb_folders(home_id?)`
- `create_kb_folder(name, home_id?, parent_id?)`
- `update_kb_folder(folder_id, home_id?, name?, parent_id?)` — same
  rename/move semantics and cycle check as the REST endpoint
- `delete_kb_folder(folder_id, home_id?)` — same non-empty guard as REST
  (raises `ValueError` if not empty)

`create_kb_entry` / `update_kb_entry` MCP tools gain an optional
`folder_id` parameter.

## Frontend

### `kbStore.svelte.ts`

- Adds `folders: KBFolder[]` state, populated from the extended
  `KBDocument` on `init()`.
- `createFolder({ name, parentId })`, `updateFolder(id, { name?, parentId? })`
  (covers both rename and move/drag), `deleteFolder(id)`.
- `updateEntry`'s patch type gains `folderId?: string | null`.

### New `KBTree.svelte` component

Replaces the flat `entry-list` div in `KBPage.svelte`. Recursively renders:

- **Folder nodes:** expand/collapse chevron, folder emoji, name, child
  count. Hover reveals a "⋯" button opening a context menu:
  - New subfolder
  - New entry here
  - Rename (inline edit, same interaction as folder creation)
  - Delete (disabled + tooltipped "Folder must be empty" when non-empty)
- **Entry nodes:** existing row style/click-to-select behavior, unchanged.
  No context menu on entries (delete stays in the content header as today).

State:
- Local `$state` `Set<string>` of expanded folder ids. New folders default
  to expanded; root-level folders default expanded on first load.

### Drag-and-drop

Native HTML5 DnD.

- Entry rows and folder rows are `draggable="true"`.
- Folder rows, plus a "root" drop zone at the top of the tree, are drop
  targets. On drop, the dragged item's `folderId`/`parentId` updates to the
  target (or `null` for the root zone).
- Dropping a folder onto itself or a descendant is rejected client-side
  (no-drop cursor), mirroring the server-side cycle check.
- Scope is reparenting only — no manual sibling reordering. Entries keep
  sorting by `createdAt`; folders sort by name.

### Search

Typing in the sidebar search box filters the tree recursively: a folder is
shown if its own name matches OR it contains a matching entry/subfolder
anywhere below it. Folders kept visible by a descendant match auto-expand.
Clearing the search restores the prior manual expand/collapse state.

### Card layout

`KBPage.svelte`'s whole page (sidebar + content) moves inside one outer
`Card`, matching the "wrap everything" style already used elsewhere (e.g.
Chores' table card). The sidebar/content split keeps its existing internal
divider border; it just now sits inside the card shell/shadow instead of
directly on the page background.

The sidebar toolbar gains a `+ Folder` button next to the existing
`+ New` (entry) button — creates a root-level folder named "New folder"
and immediately opens inline rename.

## Testing

**Backend** (`test_kb.py` + new `test_kb_folders.py`):
- Folder CRUD; non-empty delete rejected (400); cycle rejected on move
  (400); `KBDocument` returns both entries and folders; entry `folderId`
  round-trips through markdown frontmatter.

**MCP** (`test_mcp_tools_kb.py`):
- New folder tools follow the existing role-check (`ro`/`normal`) and
  error-raising conventions of the entry tools.

**Frontend** (`kbStore.test.ts` + new `KBTree.test.ts`):
- Store: folder CRUD methods; `updateEntry` with `folderId`.
- Tree component: expand/collapse; nested rendering; search filter/auto-
  expand; drag-and-drop reparenting (incl. self/descendant rejection);
  context menu actions; inline rename.

**Edge cases:**
- Deleting a non-empty folder → blocked with a clear message.
- Dragging a folder into its own descendant → rejected.
- Entries with no `folderId` → render at root, unaffected by the change.
- Empty state ("No entries yet") still applies to a fully empty tree.

## Out of scope

- Manual sibling reordering within a folder.
- Persisting expand/collapse state across reloads.
- Migrating existing KB entry storage off markdown files (folders are new
  SQLite data; entries stay as-is with one added frontmatter field).
