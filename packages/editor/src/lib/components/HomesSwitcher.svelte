<script lang="ts">
  import { homesStore } from "../homesStore.svelte";
  import NewHomeModal from "./NewHomeModal.svelte";

  interface Props {
    expanded: boolean;
    onexpand?: () => void;
  }
  let { expanded, onexpand }: Props = $props();

  let dropdownOpen = $state(false);
  let showNewModal = $state(false);

  $effect(() => {
    if (!expanded) dropdownOpen = false;
  });

  function handleClick(): void {
    if (!expanded) { onexpand?.(); return; }
    dropdownOpen = !dropdownOpen;
  }

  function selectHome(id: string): void {
    homesStore.setActiveHomeId(id);
    dropdownOpen = false;
  }
</script>

<div class="switcher" class:expanded>
  <button
    class="current"
    onclick={handleClick}
    title={homesStore.activeHome?.name ?? "Select home"}
  >
    <span class="icon">⌂</span>
    {#if expanded}
      <span class="name">{homesStore.activeHome?.name ?? "—"}</span>
      <span class="chevron">{dropdownOpen ? "▲" : "▼"}</span>
    {/if}
  </button>

  {#if dropdownOpen}
    <div class="dropdown">
      {#each homesStore.homes as home (home.id)}
        <button
          class="home-item"
          class:active={home.id === homesStore.activeHomeId}
          onclick={() => selectHome(home.id)}
        >
          <span class="icon">{typeIcon(home.type)}</span>
          <span class="home-name">{home.name}</span>
        </button>
      {/each}
      <hr class="separator" />
      <button class="home-item add" onclick={() => { dropdownOpen = false; showNewModal = true; }}>
        <span class="icon">＋</span>
        <span class="home-name">New home</span>
      </button>
    </div>
  {/if}
</div>

<NewHomeModal open={showNewModal} onclose={() => { showNewModal = false; }} />

<style>
  .switcher { position: relative; padding: 6px 6px 4px; border-bottom: 1px solid var(--border); }

  .current {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px 8px;
    border: none;
    background: none;
    border-radius: var(--radius);
    cursor: pointer;
    color: var(--text);
    min-width: 0;
  }
  .current:hover { background: var(--surface-hover); }

  .icon { font-size: 18px; width: 20px; text-align: center; flex-shrink: 0; line-height: 1; }
  .name { font-size: 12px; font-weight: 600; flex: 1; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chevron { font-size: 10px; color: var(--text-muted); flex-shrink: 0; }

  .dropdown {
    position: absolute;
    top: calc(100% + 2px);
    left: 6px;
    right: 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 100;
    padding: 4px;
  }

  .home-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 10px;
    border: none;
    background: none;
    border-radius: var(--radius);
    cursor: pointer;
    color: var(--text);
    font-size: 13px;
    text-align: left;
  }
  .home-item:hover { background: var(--surface-hover); }
  .home-item.active { background: var(--accent); color: var(--accent-contrast); }
  .home-item.add { color: var(--text-muted); }

  .separator { border: none; border-top: 1px solid var(--border); margin: 4px 0; }
</style>
