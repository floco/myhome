<!-- packages/editor/src/lib/components/ui/FilterButton.svelte -->
<script lang="ts">
  interface Props {
    active?: boolean;
    onclick: () => void;
    title: string;
  }
  let { active = false, onclick, title }: Props = $props();
</script>

<button type="button" class="ui-filter-button" class:active {onclick} {title} aria-label={title}>
  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
    <path
      d="M2 3h12l-4.5 5.5v4l-3 1.5v-5.5z"
      fill="none" stroke="currentColor" stroke-width="1.4"
      stroke-linecap="round" stroke-linejoin="round"
    />
  </svg>
  {#if active}<span class="badge"></span>{/if}
</button>

<style>
  .ui-filter-button {
    position: relative;
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; flex-shrink: 0;
    background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-md);
    color: var(--text-muted); cursor: pointer;
  }
  .ui-filter-button:hover { background: var(--surface-hover); color: var(--text); }
  .ui-filter-button.active { color: var(--accent); border-color: var(--accent); }
  .badge {
    position: absolute; top: -3px; right: -3px;
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); border: 1.5px solid var(--surface);
  }
</style>
