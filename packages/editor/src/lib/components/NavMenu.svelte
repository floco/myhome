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
      <div class="section-header" title="Chores">
        <span class="section-icon">📋</span>
        <span class="section-title">Chores</span>
      </div>
      <div class="section-divider"></div>
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

  .nav-body { flex: 1; display: flex; flex-direction: column; min-width: 180px; }

  .nav-section { display: flex; flex-direction: column; }

  .section-header {
    display: flex; align-items: center; gap: 10px;
    height: 40px; padding: 0 12px;
    white-space: nowrap;
  }
  .section-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; line-height: 1; }
  .section-title {
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
    color: #556; font-weight: 600;
  }

  .section-divider { height: 1px; background: #1e1e38; margin: 0; }

  .nav-item {
    display: flex; align-items: center; gap: 10px;
    height: 40px; padding: 0 12px;
    color: #777; text-decoration: none; white-space: nowrap;
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
