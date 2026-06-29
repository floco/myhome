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
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
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
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="media-tile"
          role="button"
          tabindex="0"
          onclick={() => onItemClick(i)}
          onkeydown={(e) => { if (e.key === "Enter") onItemClick(i); }}
        >
          <img
            src={item.thumbnailUrl}
            alt={item.name}
            onerror={(e) => {
              const img = e.target as HTMLImageElement;
              img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 24 24'%3E%3Cpath fill='%23888' d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/%3E%3C/svg%3E";
            }}
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
