# KB Markdown Media Insert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the KB media picker (📷 toolbar button in `MarkdownEditor.svelte`) insert plain markdown text instead of a raw HTML `<a><img></a>` snippet, while keeping the S/M/L width picker and click-through-to-full-item behavior identical to today.

**Architecture:** Two changes to one file, `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`. (1) Register a custom `marked` `image` renderer that reads an optional `|<width>` suffix off the image's alt text and emits it as an HTML `width` attribute. (2) Rewrite `insertMedia()` to build `[![name|W](<imgSrc>)](<url>)` markdown instead of an HTML string. Output continues to flow through the existing `DOMPurify.sanitize(...)` call unchanged.

**Tech Stack:** Svelte 5, TypeScript, `marked` 18.0.5, `DOMPurify`, Vitest (`mount`/`unmount`/`flushSync` from `svelte`), tests in `packages/editor/test/MarkdownEditor.test.ts`.

## Global Constraints

- No migration of existing KB page content — old `<a href="..."><img ...></a>` HTML already saved in page bodies must keep rendering exactly as it does today (marked/DOMPurify already pass raw inline HTML through unchanged).
- The `🔖` bookmark-insert toolbar action and its `kb-bookmark` HTML card are out of scope — do not touch `handleInsertBookmark`.
- Preserve current click-through behavior exactly: for `type: "document"` items, the image shown is the thumbnail but the link target is the full item URL; for all other types, both the image and the link target are the item's own URL.
- Alt text sanitization must prevent an item name containing `[`, `]`, `|`, or a newline from producing malformed/ambiguous markdown.

---

### Task 1: Custom `marked` image renderer (alt|width convention)

**Files:**
- Modify: `packages/editor/src/lib/components/ui/MarkdownEditor.svelte:1-8` (imports + existing `marked.use({ breaks: true, gfm: true })` call)
- Test: `packages/editor/test/MarkdownEditor.test.ts` (new `describe` block, after the existing `"MarkdownEditor — media picker"` block, i.e. after line 374)

**Interfaces:**
- Produces: rendering behavior consumed by Task 2's inserted markdown. Any markdown image `![alt](href)` where `alt` ends in a literal `|` followed by 1+ digits renders `<img src="{href}" alt="{alt-without-suffix}" width="{digits}">`; any other image renders a plain `<img src="{href}" alt="{alt}">` with no `width` attribute (this must include images with no `|` at all, and must not break on an alt that happens to contain a `|` not followed by digits, e.g. `a|b`).

- [ ] **Step 1: Write the failing tests**

Add this block to `packages/editor/test/MarkdownEditor.test.ts`, after the `"MarkdownEditor — media picker"` `describe` block (after line 374, before `"MarkdownEditor — clickToEdit"`):

```ts
describe("MarkdownEditor — image renderer (alt|width)", () => {
  it("renders a width attribute when alt text has a |<digits> suffix", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "![photo.jpg|400](https://example.com/photo.jpg)", editing: false },
    });
    flushSync();
    const img = target.querySelector(".md-preview img") as HTMLImageElement;
    expect(img.getAttribute("src")).toBe("https://example.com/photo.jpg");
    expect(img.getAttribute("alt")).toBe("photo.jpg");
    expect(img.getAttribute("width")).toBe("400");
    unmount(app);
    target.remove();
  });

  it("renders no width attribute for a plain image with no |<digits> suffix", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "![a plain photo](https://example.com/photo.jpg)", editing: false },
    });
    flushSync();
    const img = target.querySelector(".md-preview img") as HTMLImageElement;
    expect(img.getAttribute("alt")).toBe("a plain photo");
    expect(img.hasAttribute("width")).toBe(false);
    unmount(app);
    target.remove();
  });

  it("does not treat a non-numeric suffix after | as a width", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "![a|b](https://example.com/photo.jpg)", editing: false },
    });
    flushSync();
    const img = target.querySelector(".md-preview img") as HTMLImageElement;
    expect(img.getAttribute("alt")).toBe("a|b");
    expect(img.hasAttribute("width")).toBe(false);
    unmount(app);
    target.remove();
  });

  it("HTML-escapes alt text containing special characters", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: '![a & "b"|400](https://example.com/photo.jpg)', editing: false },
    });
    flushSync();
    const img = target.querySelector(".md-preview img") as HTMLImageElement;
    expect(img.getAttribute("alt")).toBe('a & "b"');
    expect(img.getAttribute("width")).toBe("400");
    unmount(app);
    target.remove();
  });

  it("renders a link-wrapped image (nested markdown) with the width applied", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: "[![doc.pdf|200](<https://example.com/doc.pdf.thumb.jpg>)](<https://example.com/doc.pdf>)",
        editing: false,
      },
    });
    flushSync();
    const link = target.querySelector(".md-preview a") as HTMLAnchorElement;
    const img = link.querySelector("img") as HTMLImageElement;
    expect(link.getAttribute("href")).toBe("https://example.com/doc.pdf");
    expect(img.getAttribute("src")).toBe("https://example.com/doc.pdf.thumb.jpg");
    expect(img.getAttribute("width")).toBe("200");
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/MarkdownEditor.test.ts -t "image renderer"`
Expected: FAIL — none of the rendered `<img>` elements have a `width` attribute yet (no custom renderer registered), so the first, fourth, and fifth assertions on `width` fail.

- [ ] **Step 3: Implement the custom renderer**

In `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`, replace lines 1-8:

```ts
<script lang="ts">
  import { marked } from "marked";
  import DOMPurify from "dompurify";
  import { _ } from "svelte-i18n";
  import type { MediaItem } from "./mediaTypes";

  // Single newlines become <br>; GFM adds ~~strikethrough~~, tables, task lists.
  marked.use({ breaks: true, gfm: true });
```

with:

```ts
<script lang="ts">
  import { marked } from "marked";
  import DOMPurify from "dompurify";
  import { _ } from "svelte-i18n";
  import type { MediaItem } from "./mediaTypes";

  function escapeHtml(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Single newlines become <br>; GFM adds ~~strikethrough~~, tables, task lists.
  // Custom image renderer: an alt-text suffix of "|<digits>" (e.g. "photo.jpg|400",
  // the convention this editor's media picker inserts) becomes a width attribute;
  // any other image (hand-typed, pasted, or legacy content) renders unchanged.
  marked.use({
    breaks: true,
    gfm: true,
    renderer: {
      image({ href, title, text }) {
        const widthMatch = text.match(/^(.*)\|(\d+)$/);
        const alt = widthMatch ? widthMatch[1] : text;
        const width = widthMatch ? widthMatch[2] : null;
        let out = `<img src="${escapeHtml(href)}" alt="${escapeHtml(alt)}"`;
        if (width) out += ` width="${width}"`;
        if (title) out += ` title="${escapeHtml(title)}"`;
        out += ">";
        return out;
      },
    },
  });
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/MarkdownEditor.test.ts -t "image renderer"`
Expected: PASS (all 5 new tests). Then run the full file to confirm no regressions: `npx vitest run test/MarkdownEditor.test.ts` — expected: all existing tests still PASS (this task didn't touch `insertMedia`, so the S/M/L tests still assert the old HTML string until Task 2).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/MarkdownEditor.svelte packages/editor/test/MarkdownEditor.test.ts
git commit -m "feat(editor): support alt|width convention in markdown image renderer"
```

---

### Task 2: `insertMedia()` emits markdown instead of HTML

**Files:**
- Modify: `packages/editor/src/lib/components/ui/MarkdownEditor.svelte:115-139` (the `escapeAttr` and `insertMedia` functions)
- Modify: `packages/editor/test/MarkdownEditor.test.ts:257-331` (the five existing S/M/L / PDF insertion assertions, which currently expect the old HTML string)

**Interfaces:**
- Consumes: the `image` renderer registered in Task 1 (verified indirectly — this task's tests assert on the raw markdown written into the textarea, not on rendered HTML, so it doesn't call into Task 1's code directly, but the format it produces — `[![name|W](<imgSrc>)](<url>)` — must match exactly what Task 1's renderer/tests expect).
- Produces: nothing consumed by a later task (this is the last task).

- [ ] **Step 1: Update the existing insertion tests to expect markdown**

In `packages/editor/test/MarkdownEditor.test.ts`, replace the five assertions in the `"MarkdownEditor — media picker"` block:

Replace (line 270):
```ts
    expect(textarea.value).toBe('<a href="/api/kb/e1/attachments/photo.jpg"><img src="/api/kb/e1/attachments/photo.jpg" width="200" alt="photo.jpg"></a>');
```
with:
```ts
    expect(textarea.value).toBe("[![photo.jpg|200](</api/kb/e1/attachments/photo.jpg>)](</api/kb/e1/attachments/photo.jpg>)");
```

Replace (line 289):
```ts
    expect(textarea.value).toBe('<a href="/api/kb/e1/attachments/photo.jpg"><img src="/api/kb/e1/attachments/photo.jpg" width="400" alt="photo.jpg"></a>');
```
with:
```ts
    expect(textarea.value).toBe("[![photo.jpg|400](</api/kb/e1/attachments/photo.jpg>)](</api/kb/e1/attachments/photo.jpg>)");
```

Replace (line 307):
```ts
    expect(textarea.value).toBe('<a href="/api/kb/e1/attachments/photo.jpg"><img src="/api/kb/e1/attachments/photo.jpg" width="600" alt="photo.jpg"></a>');
```
with:
```ts
    expect(textarea.value).toBe("[![photo.jpg|600](</api/kb/e1/attachments/photo.jpg>)](</api/kb/e1/attachments/photo.jpg>)");
```

Replace (lines 325-327):
```ts
    expect(textarea.value).toBe(
      '<a href="/api/kb/e1/attachments/doc.pdf"><img src="/api/kb/e1/attachments/doc.pdf.thumb.jpg" width="200" alt="doc.pdf"></a>',
    );
```
with:
```ts
    expect(textarea.value).toBe(
      "[![doc.pdf|200](</api/kb/e1/attachments/doc.pdf.thumb.jpg>)](</api/kb/e1/attachments/doc.pdf>)",
    );
```

Then add one new test in the same `describe` block, after the PDF test (after what is currently line 331, before the "pressing Escape" test):

```ts
  it("strips markdown-breaking characters ([ ] | newline) from the inserted alt text", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const weirdItem: MediaItem = {
      id: "weird",
      name: "photo [1]|two\nlines.jpg",
      url: "/api/kb/e1/attachments/weird.jpg",
      thumbnailUrl: "/api/kb/e1/attachments/weird.jpg",
      type: "image",
    };
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [weirdItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelector('[data-size="s"]') as HTMLButtonElement).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    // sanitizeAlt replaces each of [ ] | \n individually with a space (no
    // collapsing of adjacent spaces), so "[1]|" becomes "  1  " (double spaces).
    expect(textarea.value).toBe(
      "[![photo  1  two lines.jpg|200](</api/kb/e1/attachments/weird.jpg>)](</api/kb/e1/attachments/weird.jpg>)",
    );
    unmount(app);
    target.remove();
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/MarkdownEditor.test.ts -t "media picker"`
Expected: FAIL — `insertMedia` still produces the old HTML string, and the new sanitization test fails because `sanitizeAlt` doesn't exist yet.

- [ ] **Step 3: Rewrite `insertMedia` and drop the now-unused `escapeAttr`**

In `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`, replace lines 115-139:

```ts
  function escapeAttr(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Allow relative paths and http/https absolute URLs; block javascript:, data:, etc.
  function safeUrl(u: string): string {
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(u)) {
      const scheme = u.split(":")[0].toLowerCase();
      return scheme === "http" || scheme === "https" ? u : "#";
    }
    return u;
  }

  function insertMedia(item: MediaItem, width: number): void {
    const name = escapeAttr(item.name);
    const url = escapeAttr(safeUrl(item.url));
    const thumb = escapeAttr(safeUrl(item.thumbnailUrl));
    const w = Math.floor(Number(width));
    const md =
      item.type === "document"
        ? `<a href="${url}"><img src="${thumb}" width="${w}" alt="${name}"></a>`
        : `<a href="${url}"><img src="${url}" width="${w}" alt="${name}"></a>`;
    insert(md);
    pickerOpen = false;
  }
```

with:

```ts
  // Allow relative paths and http/https absolute URLs; block javascript:, data:, etc.
  function safeUrl(u: string): string {
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(u)) {
      const scheme = u.split(":")[0].toLowerCase();
      return scheme === "http" || scheme === "https" ? u : "#";
    }
    return u;
  }

  // Strip characters that would break the "[![alt|width](url)](url)" markdown
  // this builds: [ ] would prematurely close the alt/link text, | collides with
  // the width-suffix delimiter, and newlines would break out of the line.
  function sanitizeAlt(s: string): string {
    return s.replace(/[[\]|\n]/g, " ");
  }

  function insertMedia(item: MediaItem, width: number): void {
    const name = sanitizeAlt(item.name);
    const url = safeUrl(item.url);
    const imgSrc = item.type === "document" ? safeUrl(item.thumbnailUrl) : url;
    const w = Math.floor(Number(width));
    insert(`[![${name}|${w}](<${imgSrc}>)](<${url}>)`);
    pickerOpen = false;
  }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/MarkdownEditor.test.ts`
Expected: PASS — full file, all tests (media picker, image renderer, and every other existing `describe` block).

- [ ] **Step 5: Run the full editor test suite**

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: PASS — no regressions in other components (e.g. `KBPage.test.ts` if it exercises `MarkdownEditor` indirectly).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ui/MarkdownEditor.svelte packages/editor/test/MarkdownEditor.test.ts
git commit -m "feat(editor): insert markdown instead of HTML from the KB media picker"
```
