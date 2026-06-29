<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { MediaItem } from "./mediaTypes";

  interface Props {
    items: MediaItem[];
    initialIndex: number;
    onclose: () => void;
  }

  let { items, initialIndex, onclose }: Props = $props();

  let index = $state(initialIndex);
  const current = $derived(items[index]);

  function prev() { if (index > 0) index--; }
  function next() { if (index < items.length - 1) index++; }

  function handleKey(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
    else if (e.key === "ArrowLeft") prev();
    else if (e.key === "ArrowRight") next();
  }

  onMount(() => { document.addEventListener("keydown", handleKey); });
  onDestroy(() => { document.removeEventListener("keydown", handleKey); });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="lightbox-overlay" onclick={onclose}>
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="lightbox-content" onclick={(e) => e.stopPropagation()}>
    {#if index > 0}
      <button class="arrow-prev" onclick={prev}>‹</button>
    {/if}

    <div class="lightbox-media">
      <img
        class="lightbox-img"
        src={current.thumbnailUrl}
        alt={current.name}
        onerror={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
      />
      {#if current.type === "document"}
        <a
          class="lightbox-open-btn"
          href={current.url}
          target="_blank"
          rel="noopener"
          onclick={(e) => e.stopPropagation()}
        >Open PDF ↗</a>
      {/if}
    </div>

    {#if index < items.length - 1}
      <button class="arrow-next" onclick={next}>›</button>
    {/if}
  </div>

  <div class="lightbox-bar" onclick={(e) => e.stopPropagation()}>
    <span class="lightbox-name">{current.name}</span>
    <span class="lightbox-counter">{index + 1} / {items.length}</span>
  </div>
</div>

<style>
  .lightbox-overlay {
    position: fixed; inset: 0; z-index: 200;
    background: rgba(0,0,0,0.88);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }
  .lightbox-content {
    position: relative; display: flex; align-items: center; justify-content: center;
    max-width: 90vw; max-height: 80vh;
  }
  .lightbox-media { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .lightbox-img { max-width: 80vw; max-height: 72vh; object-fit: contain; border-radius: var(--radius-md); }
  .lightbox-open-btn {
    background: var(--accent); color: #fff; padding: 8px 20px;
    border-radius: var(--radius-md); text-decoration: none; font-size: 13px;
    font-family: var(--font-sans);
  }
  .lightbox-open-btn:hover { opacity: 0.88; }
  .arrow-prev, .arrow-next {
    position: absolute; top: 50%; transform: translateY(-50%);
    background: rgba(0,0,0,0.5); border: none; color: #fff;
    font-size: 32px; width: 44px; height: 44px; border-radius: 50%;
    cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 1;
  }
  .arrow-prev { left: -56px; }
  .arrow-next { right: -56px; }
  .arrow-prev:hover, .arrow-next:hover { background: rgba(0,0,0,0.75); }
  .lightbox-bar {
    display: flex; gap: 16px; align-items: center; margin-top: 16px;
    color: rgba(255,255,255,0.7); font-size: 12px; font-family: var(--font-sans);
  }
  .lightbox-name { color: #fff; }
  .lightbox-counter { color: rgba(255,255,255,0.5); }
</style>
