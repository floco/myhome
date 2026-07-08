<!-- packages/editor/src/lib/components/settings/SettingsNav.svelte -->
<script lang="ts">
  interface SettingsGroup {
    id: string;
    icon: string;
    label: string;
  }

  interface Props {
    groups: SettingsGroup[];
    active: string;
    onchange: (id: string) => void;
  }
  let { groups, active, onchange }: Props = $props();
</script>

<nav class="settings-nav">
  {#each groups as group (group.id)}
    <button
      class="nav-item"
      class:active={group.id === active}
      onclick={() => onchange(group.id)}
    >
      <span class="nav-icon">{group.icon}</span>
      <span class="nav-label">{group.label}</span>
    </button>
  {/each}
</nav>

<div class="settings-nav-mobile">
  <select
    class="nav-select"
    value={active}
    onchange={(e) => onchange((e.target as HTMLSelectElement).value)}
  >
    {#each groups as group (group.id)}
      <option value={group.id}>{group.icon} {group.label}</option>
    {/each}
  </select>
</div>

<style>
  .settings-nav {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 200px;
    flex-shrink: 0;
    padding: var(--space-3);
    border-right: 1px solid var(--border);
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-radius: var(--radius);
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 13px;
    font-family: var(--font-sans);
    text-align: left;
    cursor: pointer;
  }
  .nav-item:hover { background: var(--surface-hover); color: var(--text); }
  .nav-item.active { background: var(--surface-alt); color: var(--text); font-weight: 600; }
  .nav-icon { font-size: 15px; width: 18px; text-align: center; }
  .settings-nav-mobile { display: none; }
  .nav-select {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 10px;
    color: var(--text);
    font-size: 13px;
    font-family: var(--font-sans);
  }

  @media (max-width: 720px) {
    .settings-nav { display: none; }
    .settings-nav-mobile { display: block; padding: var(--space-3); border-bottom: 1px solid var(--border); }
  }
</style>
