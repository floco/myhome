<script lang="ts">
  interface Tab { id: string; label: string; disabled?: boolean; }
  interface Props {
    tabs: Tab[];
    active: string;
    onchange: (id: string) => void;
  }
  let { tabs, active, onchange }: Props = $props();
</script>
<div class="tab-bar">
  {#each tabs as tab}
    <button
      class="tab"
      class:active={tab.id === active}
      disabled={tab.disabled}
      onclick={() => { if (!tab.disabled) onchange(tab.id); }}
    >{tab.label}</button>
  {/each}
</div>
<style>
  .tab-bar { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab { padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans); }
  .tab:hover:not(:disabled) { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }
  .tab:disabled { color: var(--text-faint); cursor: default; }
</style>
