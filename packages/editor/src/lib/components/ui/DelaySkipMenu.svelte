<script lang="ts">
  import { _ } from "svelte-i18n";
  import Popover from "./Popover.svelte";
  import type { DelayUnit } from "../../choreStore.svelte";

  interface Props {
    title?: string;
    onDelay: (unit: DelayUnit) => void;
    onSkip: () => void;
  }
  let { title, onDelay, onSkip }: Props = $props();

  let open = $state(false);
  let anchorEl = $state<HTMLElement | null>(null);

  function pick(fn: () => void): void {
    open = false;
    fn();
  }
</script>

<button
  type="button"
  class="icon-btn"
  title={title ?? $_('chores.page.delayOrSkip')}
  bind:this={anchorEl}
  onclick={() => { open = !open; }}
>⏭</button>

<Popover {open} {anchorEl} onclose={() => { open = false; }} width={200}>
  <button type="button" class="dsm-item" onclick={() => pick(() => onDelay("week"))}>{$_('chores.page.delayByWeek')}</button>
  <button type="button" class="dsm-item" onclick={() => pick(() => onDelay("month"))}>{$_('chores.page.delayByMonth')}</button>
  <button type="button" class="dsm-item" onclick={() => pick(() => onDelay("year"))}>{$_('chores.page.delayByYear')}</button>
  <div class="dsm-sep"></div>
  <button type="button" class="dsm-item" onclick={() => pick(onSkip)}>{$_('chores.page.skipToNext')}</button>
</Popover>

<style>
  .icon-btn {
    padding: 6px 10px; border: none; border-radius: var(--radius-sm);
    background: var(--surface-alt); color: var(--text-muted); cursor: pointer; font-size: 13px;
    min-height: 30px;
  }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .dsm-item {
    display: block; width: 100%; text-align: left;
    font-family: var(--font-sans); font-size: 12px;
    padding: 6px 8px; border: none; border-radius: var(--radius-sm);
    background: none; color: var(--text); cursor: pointer;
  }
  .dsm-item:hover { background: var(--surface-hover); }
  .dsm-sep { height: 1px; background: var(--border); margin: 4px 2px; }
</style>
