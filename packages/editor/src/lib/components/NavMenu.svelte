<script lang="ts">
  interface Props {
    currentRoute: string;
    expanded: boolean;
    onclose: () => void;
  }
  let { currentRoute, expanded, onclose }: Props = $props();
</script>

{#if expanded}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div class="backdrop" role="presentation" onclick={onclose}></div>
{/if}

<nav class="nav" class:expanded>
  <div class="nav-body">
    <div class="nav-section">
      <span class="section-label">Chores</span>
      <a href="#/" class="nav-item" class:active={currentRoute === "#/" || currentRoute === ""} title="Floor Plan" onclick={onclose}>
        <span class="nav-icon">⊞</span>
        <span class="nav-label">Floor Plan</span>
      </a>
      <a href="#/chores" class="nav-item" class:active={currentRoute === "#/chores"} title="Management" onclick={onclose}>
        <span class="nav-icon">⚙</span>
        <span class="nav-label">Management</span>
      </a>
      <a href="#/chores/list" class="nav-item" class:active={currentRoute === "#/chores/list"} title="List" onclick={onclose}>
        <span class="nav-icon">≡</span>
        <span class="nav-label">List</span>
      </a>
    </div>
  </div>
</nav>

<style>
  .backdrop {
    position: fixed; inset: 0; z-index: 19;
    background: rgba(0, 0, 0, 0.45);
  }

  .nav {
    position: relative; z-index: 20;
    display: flex; flex-direction: column;
    width: 44px; flex-shrink: 0;
    background: #14142a; border-right: 1px solid #2a2a3a;
    overflow: hidden;
    transition: width 0.18s ease;
  }
  .nav.expanded { width: 180px; }

  .nav-body { flex: 1; display: flex; flex-direction: column; padding-top: 6px; min-width: 180px; }

  .nav-section { display: flex; flex-direction: column; }

  .section-label {
    font-size: 9px; text-transform: uppercase; letter-spacing: 0.1em;
    color: #454560; padding: 6px 14px 6px;
    white-space: nowrap;
  }

  .nav-item {
    display: flex; align-items: center; gap: 12px;
    height: 40px; padding: 0 12px;
    color: #888; text-decoration: none; white-space: nowrap;
    border-left: 2px solid transparent;
  }
  .nav-item:hover { background: #1e1e3a; color: #ccc; }
  .nav-item.active { color: #aab; border-left-color: #5566cc; background: #1c1c38; }

  .nav-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; line-height: 1; }
  .nav-label { font-size: 12px; }

  @media (max-width: 600px) {
    .nav {
      position: fixed;
      top: 36px; bottom: 0; left: 0;
      width: 0;
    }
    .nav.expanded { width: 200px; }
  }
</style>
