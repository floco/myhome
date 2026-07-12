<script lang="ts">
  import { homesStore } from "../homesStore.svelte";
  import NewHomeModal from "./NewHomeModal.svelte";

  interface Props {
    expanded?: boolean;
    onexpand?: () => void;
    topbar?: boolean;
  }
  let { expanded = false, onexpand, topbar = false }: Props = $props();

  let dropdownOpen = $state(false);
  let showNewModal = $state(false);

  $effect(() => {
    if (!expanded && !topbar) dropdownOpen = false;
  });

  function handleClick(): void {
    if (topbar) { dropdownOpen = !dropdownOpen; return; }
    if (!expanded) { onexpand?.(); return; }
    dropdownOpen = !dropdownOpen;
  }

  function handleClickOutside(e: MouseEvent): void {
    if (!(e.target as HTMLElement).closest(".switcher-topbar, .switcher")) dropdownOpen = false;
  }

  function selectHome(id: string): void {
    homesStore.setActiveHomeId(id);
    dropdownOpen = false;
  }

  function typeIcon(type: string): string {
    if (type === "project") return "🏗";
    if (type === "demo") return "🧪";
    return "🏠";
  }
</script>

<svelte:window onclick={handleClickOutside} />

{#if topbar}
  <div class="switcher-topbar">
    <button
      class="topbar-current"
      onclick={handleClick}
      title={homesStore.activeHome?.name ?? "Select home"}
    >
      <span class="topbar-icon">⌂</span>
      <span class="topbar-name">{homesStore.activeHome?.name ?? "—"}</span>
      <span class="topbar-chevron">{dropdownOpen ? "▲" : "▼"}</span>
    </button>

    {#if dropdownOpen}
      <div class="topbar-dropdown">
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
{:else}
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
{/if}

<NewHomeModal open={showNewModal} onclose={() => { showNewModal = false; }} />

<style>
  /* ── Sidebar (default) variant ── */
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

  /* ── Topbar variant ── */
  .switcher-topbar { position: relative; }

  .topbar-current {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 8px; border: none; background: none;
    border-radius: var(--radius-sm); cursor: pointer; color: var(--text);
    font-size: 13px; font-weight: 500;
  }
  .topbar-current:hover { background: var(--surface-hover); }

  .topbar-icon { font-size: 15px; line-height: 1; }
  .topbar-name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .topbar-chevron { font-size: 9px; color: var(--text-muted); }

  .topbar-dropdown {
    position: absolute; top: calc(100% + 4px); left: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 200; padding: 4px; min-width: 160px;
  }
</style>
