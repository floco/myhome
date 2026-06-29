import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import MarkdownEditor from "../src/lib/components/ui/MarkdownEditor.svelte";

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
