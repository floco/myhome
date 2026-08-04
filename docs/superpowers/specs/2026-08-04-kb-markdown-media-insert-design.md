# KB markdown media insert — design

## Problem

`MarkdownEditor.svelte`'s media picker (📷 toolbar button, used only on KB pages)
inserts a raw HTML snippet at the cursor:

```html
<a href="URL"><img src="URL" width="400" alt="chaudiere_pression_2.jpg"></a>
```

The user wants the editor content to stay readable/portable markdown instead of
embedded HTML when inserting a photo or document from the media picker.

## Goals

- Media picker inserts plain markdown text, not an HTML tag.
- The S/M/L size picker (200/400/600px) keeps working — same visual result as today.
- Documents keep rendering as a clickable thumbnail linking to the full file; photos
  keep rendering as a clickable image linking to the full-size original — both
  exactly matching today's behavior.
- Existing KB pages that already contain the old HTML form keep rendering correctly,
  unchanged (no migration).

## Non-goals

- No change to the separate "insert bookmark" toolbar action (🔖) — that already
  inserts a purpose-built HTML card (`kb-bookmark`), which is unrelated to this
  ask and stays as-is.
- No change to `MediaGallery`-based attachment UIs in Works/Insurance/etc. — those
  don't use `MarkdownEditor`'s media picker at all (confirmed via repo search).

## Design

### Markdown format

Plain markdown has no syntax for image width, so width is encoded in the alt text
using the `alt|width` convention (same one Obsidian uses), which is plain text and
degrades gracefully in any other markdown viewer (worst case: the width suffix shows
up as literal alt text).

Both media types render as a link-wrapped image, matching current behavior exactly:

```
[![name|400](<imgSrc>)](<url>)
```

- `imgSrc` = the item's thumbnail URL for `type: "document"`, the item's own URL for
  everything else (this already matches the current two HTML branches).
- `url` = the full item URL (link target either way).
- Angle brackets around both URLs (`<url>`) are standard CommonMark destination
  syntax and safely handle filenames containing parentheses or spaces, which a bare
  `(url)` destination cannot.
- The item's `name` is passed through a small sanitizer that strips `[`, `]`, `|`,
  and newlines before insertion, since those characters would otherwise break the
  markdown image/link syntax being constructed.

### Rendering

`marked` is configured (`MarkdownEditor.svelte`, near the existing
`marked.use({ breaks: true, gfm: true })`) with a custom `image` renderer that:

1. Splits the alt text on a trailing `|<digits>` — if present, emits `width="…"` on
   the `<img>`; if absent (e.g. an image a user typed by hand, or a bare
   `![alt](url)` pasted in from elsewhere), emits a plain `<img>` with no width.
2. HTML-escapes the alt text and href the same way `marked`'s built-in image
   renderer already does.

Output continues to flow through the existing `DOMPurify.sanitize(...)` call
unchanged — no sanitizer config changes needed (it already allows `img`/`a`/`width`,
which is how the current HTML form renders safely today).

### Migration

None. Old KB pages with the literal `<a href="..."><img ...></a>` HTML already saved
in their content keep working: `marked`/`DOMPurify` pass raw inline HTML through
today, and that isn't changing. This only changes what *new* insertions produce.

## Testing

- Unit test for the new `image` renderer: with/without a `|width` suffix, escaping
  of alt/href.
- Unit test for `insertMedia`: correct markdown produced for both `document` and
  non-document media types, including a name containing `[`, `]`, or `|`.
- Existing `MarkdownEditor` component tests (picker open/close, S/M/L buttons) keep
  passing against the new insertion format.
