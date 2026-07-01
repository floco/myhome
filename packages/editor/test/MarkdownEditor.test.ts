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
    expect(textarea.value).toBe('<img src="/api/kb/e1/attachments/photo.jpg" width="200" alt="photo.jpg">');
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
    expect(textarea.value).toBe('<img src="/api/kb/e1/attachments/photo.jpg" width="400" alt="photo.jpg">');
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
    expect(textarea.value).toBe('<img src="/api/kb/e1/attachments/photo.jpg" width="600" alt="photo.jpg">');
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
      '<a href="/api/kb/e1/attachments/doc.pdf"><img src="/api/kb/e1/attachments/doc.pdf.thumb.jpg" width="200" alt="doc.pdf"></a>',
    );
    expect(target.querySelector(".media-picker")).toBeNull();
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
