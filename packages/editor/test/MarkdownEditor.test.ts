import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import MarkdownEditor from "../src/lib/components/ui/MarkdownEditor.svelte";
import type { MediaItem } from "../src/lib/components/ui/mediaTypes";

describe("MarkdownEditor — preview mode", () => {
  it("renders markdown as HTML in preview mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "# Hello\n\nWorld", editing: false },
    });
    flushSync();
    expect(target.querySelector(".md-preview")).not.toBeNull();
    expect(target.querySelector(".md-preview h1")?.textContent?.trim()).toBe("Hello");
    expect(target.querySelector(".md-preview p")?.textContent?.trim()).toBe("World");
    unmount(app);
    target.remove();
  });

  it("renders single newlines as <br> (breaks mode)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "line one\nline two", editing: false },
    });
    flushSync();
    expect(target.querySelector(".md-preview")!.innerHTML).toContain("<br");
    unmount(app);
    target.remove();
  });

  it("shows placeholder when value is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: false, placeholder: "Start writing…" },
    });
    flushSync();
    expect(target.querySelector(".md-placeholder")?.textContent?.trim()).toBe("Start writing…");
    unmount(app);
    target.remove();
  });

  it("applies md-empty class when value is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: false },
    });
    flushSync();
    expect(target.querySelector(".md-preview.md-empty")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking preview switches to edit mode (textarea appears)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "some content", editing: false },
    });
    flushSync();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — edit mode", () => {
  it("renders textarea with current value in edit mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "# Hello", editing: true },
    });
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea).not.toBeNull();
    expect(textarea.value).toBe("# Hello");
    unmount(app);
    target.remove();
  });

  it("does not show preview div in edit mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: true },
    });
    flushSync();
    expect(target.querySelector(".md-preview")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("applies minHeight style to textarea", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, minHeight: "400px" },
    });
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.style.minHeight).toBe("400px");
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — toolbar", () => {
  it("shows toolbar in edit mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true },
    });
    flushSync();
    expect(target.querySelector(".md-toolbar")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("hides toolbar in preview mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false },
    });
    flushSync();
    expect(target.querySelector(".md-toolbar")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("toolbar has heading, bold, italic, list, code and link buttons", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true },
    });
    flushSync();
    const titles = [...target.querySelectorAll(".tb-btn")].map(b => b.getAttribute("title"));
    expect(titles).toContain("Heading 1");
    expect(titles).toContain("Heading 2");
    expect(titles).toContain("Bold");
    expect(titles).toContain("Italic");
    expect(titles).toContain("Bullet list");
    expect(titles).toContain("Inline code");
    expect(titles).toContain("Link");
    unmount(app);
    target.remove();
  });

  it("Bold button inserts ** markers into value", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true },
    });
    flushSync();
    const boldBtn = [...target.querySelectorAll(".tb-btn")].find(
      b => b.getAttribute("title") === "Bold",
    ) as HTMLButtonElement;
    boldBtn.click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toContain("**");
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — media picker", () => {
  const imgItem: MediaItem = {
    id: "photo.jpg",
    name: "photo.jpg",
    url: "/api/kb/e1/attachments/photo.jpg",
    thumbnailUrl: "/api/kb/e1/attachments/photo.jpg",
    type: "image",
  };
  const pdfItem: MediaItem = {
    id: "doc.pdf",
    name: "doc.pdf",
    url: "/api/kb/e1/attachments/doc.pdf",
    thumbnailUrl: "/api/kb/e1/attachments/doc.pdf.thumb.jpg",
    type: "document",
  };

  it("does not show 📷 button when mediaItems prop is omitted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true } });
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).toBeNull();
    unmount(app);
    target.remove();
  });

  it("does not show 📷 button when mediaItems is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [] },
    });
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).toBeNull();
    unmount(app);
    target.remove();
  });

  it("shows 📷 button when mediaItems are provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    expect(target.querySelector('[title="Insert media"]')).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking 📷 button opens picker panel", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    expect(target.querySelector(".media-picker")).toBeNull();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector(".media-picker")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("S size button inserts image at 200px width and closes picker", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelector('[data-size="s"]') as HTMLButtonElement).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("[![photo.jpg|200](</api/kb/e1/attachments/photo.jpg>)](</api/kb/e1/attachments/photo.jpg>)");
    expect(target.querySelector(".media-picker")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("M size button inserts image at 400px width", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelector('[data-size="m"]') as HTMLButtonElement).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("[![photo.jpg|400](</api/kb/e1/attachments/photo.jpg>)](</api/kb/e1/attachments/photo.jpg>)");
    unmount(app);
    target.remove();
  });

  it("L size button inserts image at 600px width", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelector('[data-size="l"]') as HTMLButtonElement).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("[![photo.jpg|600](</api/kb/e1/attachments/photo.jpg>)](</api/kb/e1/attachments/photo.jpg>)");
    unmount(app);
    target.remove();
  });

  it("S size button inserts PDF as linked thumbnail at 200px width and closes picker", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [pdfItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    (target.querySelector('[data-size="s"]') as HTMLButtonElement).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe(
      "[![doc.pdf|200](</api/kb/e1/attachments/doc.pdf.thumb.jpg>)](</api/kb/e1/attachments/doc.pdf>)",
    );
    expect(target.querySelector(".media-picker")).toBeNull();
    unmount(app);
    target.remove();
  });

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

  it("pressing Escape closes picker without inserting", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector(".media-picker")).not.toBeNull();
    target.querySelector(".tb-media-wrap")!.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
    flushSync();
    expect(target.querySelector(".media-picker")).toBeNull();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    unmount(app);
    target.remove();
  });

  it("clicking outside the picker closes it without inserting", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, mediaItems: [imgItem] },
    });
    flushSync();
    (target.querySelector('[title="Insert media"]') as HTMLButtonElement).click();
    flushSync();
    expect(target.querySelector(".media-picker")).not.toBeNull();
    document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(target.querySelector(".media-picker")).toBeNull();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    unmount(app);
    target.remove();
  });
});

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

describe("MarkdownEditor — clickToEdit", () => {
  it("clicking preview enters edit mode by default", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking preview does not enter edit mode when clickToEdit is false", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false, clickToEdit: false },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    expect(target.querySelector(".md-preview")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("preview has md-clickable class when clickToEdit is true", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false, clickToEdit: true },
    });
    flushSync();
    expect(target.querySelector(".md-preview.md-clickable")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("preview does not have md-clickable class when clickToEdit is false", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false, clickToEdit: false },
    });
    flushSync();
    expect(target.querySelector(".md-preview.md-clickable")).toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — editTrigger", () => {
  it("double-click enters edit mode when editTrigger is dblclick", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false, editTrigger: "dblclick" },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).dispatchEvent(
      new MouseEvent("dblclick", { bubbles: true }),
    );
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("a single click does not enter edit mode when editTrigger is dblclick", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false, editTrigger: "dblclick" },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("defaults to single-click behavior when editTrigger is omitted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — resolveKbLink", () => {
  it("replaces the link text with the live title and icon when resolvable", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: "See [stale text](#/kb/p1) for details",
        editing: false,
        resolveKbLink: (id: string) => (id === "p1" ? { title: "Current Title", icon: "🔧" } : null),
      },
    });
    flushSync();
    const link = target.querySelector("a.kb-link");
    expect(link).not.toBeNull();
    expect(link?.textContent).toBe("🔧 Current Title");
    unmount(app);
    target.remove();
  });

  it("renders a Page deleted chip when the link cannot be resolved", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: "See [old link](#/kb/gone) for details",
        editing: false,
        resolveKbLink: () => null,
      },
    });
    flushSync();
    const chip = target.querySelector("a.kb-link-deleted");
    expect(chip).not.toBeNull();
    expect(chip?.textContent).toBe("Page deleted");
    expect(chip?.hasAttribute("href")).toBe(false);
    unmount(app);
    target.remove();
  });

  it("leaves non-kb links untouched", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: "[External](https://example.com)",
        editing: false,
        resolveKbLink: () => null,
      },
    });
    flushSync();
    const link = target.querySelector("a[href='https://example.com']");
    expect(link?.textContent).toBe("External");
    unmount(app);
    target.remove();
  });

  it("does not alter kb links when resolveKbLink is not provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "[Some text](#/kb/p1)", editing: false },
    });
    flushSync();
    const link = target.querySelector("a[href='#/kb/p1']");
    expect(link?.textContent).toBe("Some text");
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — external link target", () => {
  it("opens a plain external link in a new tab with rel=noopener noreferrer", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "[External](https://example.com)", editing: false },
    });
    flushSync();
    const link = target.querySelector("a[href='https://example.com']");
    expect(link?.getAttribute("target")).toBe("_blank");
    expect(link?.getAttribute("rel")).toBe("noopener noreferrer");
    unmount(app);
    target.remove();
  });

  it("does not add target/rel to an internal #/kb/ link", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "[Some text](#/kb/p1)", editing: false },
    });
    flushSync();
    const link = target.querySelector("a[href='#/kb/p1']");
    expect(link?.hasAttribute("target")).toBe(false);
    expect(link?.hasAttribute("rel")).toBe(false);
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — /page slash command", () => {
  it("replaces /page with a link to the created child page", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onSlashPage = async () => ({ id: "new-child", title: "New page" });
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, onSlashPage },
    });
    flushSync();
    const textarea = target.querySelector(".md-editor") as HTMLTextAreaElement;
    textarea.value = "/page";
    textarea.selectionStart = 5;
    textarea.selectionEnd = 5;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(textarea.value).toBe("[New page](#/kb/new-child)");
    unmount(app);
    target.remove();
  });

  it("does nothing when onSlashPage is not provided", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true },
    });
    flushSync();
    const textarea = target.querySelector(".md-editor") as HTMLTextAreaElement;
    textarea.value = "/page";
    textarea.selectionStart = 5;
    textarea.selectionEnd = 5;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(textarea.value).toBe("/page");
    unmount(app);
    target.remove();
  });

  it("does nothing when onSlashPage resolves to null", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onSlashPage = async () => null;
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, onSlashPage },
    });
    flushSync();
    const textarea = target.querySelector(".md-editor") as HTMLTextAreaElement;
    textarea.value = "/page";
    textarea.selectionStart = 5;
    textarea.selectionEnd = 5;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(textarea.value).toBe("/page");
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — bookmark insert", () => {
  it("does not show 🔖 button when onInsertBookmark is omitted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true } });
    flushSync();
    expect(target.querySelector('[title="Insert bookmark"]')).toBeNull();
    unmount(app);
    target.remove();
  });

  it("shows 🔖 button when onInsertBookmark is provided", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onInsertBookmark = async () => null;
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true, onInsertBookmark } });
    flushSync();
    expect(target.querySelector('[title="Insert bookmark"]')).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking 🔖 button inserts the resolved HTML at the cursor", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onInsertBookmark = async () => '<a class="kb-bookmark" href="https://example.com">Example</a>';
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true, onInsertBookmark } });
    flushSync();
    (target.querySelector('[title="Insert bookmark"]') as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe('<a class="kb-bookmark" href="https://example.com">Example</a>');
    unmount(app);
    target.remove();
  });

  it("clicking 🔖 button does nothing when onInsertBookmark resolves to null", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onInsertBookmark = async () => null;
    const app = mount(MarkdownEditor, { target, props: { value: "", editing: true, onInsertBookmark } });
    flushSync();
    (target.querySelector('[title="Insert bookmark"]') as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — DOMPurify target attribute", () => {
  it('preserves target="_blank" on rendered links (needed for bookmark cards to open in a new tab)', () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: {
        value: '<a class="kb-bookmark" href="https://example.com" target="_blank" rel="noopener noreferrer">Example</a>',
        editing: false,
      },
    });
    flushSync();
    const link = target.querySelector("a.kb-bookmark");
    expect(link?.getAttribute("target")).toBe("_blank");
    unmount(app);
    target.remove();
  });
});
