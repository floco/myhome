<script lang="ts">
  interface Props {
    currentRoute: string;
    expanded: boolean;
    onclose: () => void;
  }
  let { currentRoute, expanded, onclose }: Props = $props();

  const modules = [
    { href: "#/",            icon: "🏡", label: "Home"         },
    { href: "#/plan",        icon: "🏠", label: "Floor Plan"   },
    { href: "#/chores",      icon: "✅", label: "Chores"       },
    { href: "#/inventory",   icon: "📦", label: "Inventory"    },
    { href: "#/consumables", icon: "🛒", label: "Consumables"  },
    { href: "#/works",       icon: "🔧", label: "Works"        },
    { href: "#/costs",       icon: "💶", label: "Costs"        },
  ];

  const settingsLink = { href: "#/settings", icon: "⚙️", label: "Settings" };

  function isActive(href: string): boolean {
    if (href === "#/") return currentRoute === "#/" || currentRoute === "";
    return currentRoute.startsWith(href);
  }
</script>

{#if expanded}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div class="backdrop" role="presentation" onclick={onclose}></div>
{/if}

<nav class="nav" class:expanded>
  <div class="nav-body">
    {#each modules as mod}
      <a
        href={mod.href}
        class="nav-item"
        class:active={isActive(mod.href)}
        title={mod.label}
        onclick={onclose}
      >
        <span class="nav-icon">{mod.icon}</span>
        <span class="nav-label">{mod.label}</span>
      </a>
    {/each}
    <hr class="nav-separator" />
    <a
      href={settingsLink.href}
      class="nav-item"
      class:active={isActive(settingsLink.href)}
      title={settingsLink.label}
      onclick={onclose}
    >
      <span class="nav-icon">{settingsLink.icon}</span>
      <span class="nav-label">{settingsLink.label}</span>
    </a>
  </div>
</nav>

<style>
  .backdrop {
    display: none;
    position: fixed; inset: 0; z-index: 19;
    background: rgba(0, 0, 0, 0.45);
  }
  @media (max-width: 600px) {
    .backdrop { display: block; }
  }

  .nav {
    position: relative; z-index: 20;
    display: flex; flex-direction: column;
    width: 44px; flex-shrink: 0;
    background: var(--surface); border-right: 1px solid var(--border);
    overflow: hidden;
    transition: width 0.18s ease;
  }
  .nav.expanded { width: 180px; }

  .nav-body { flex: 1; display: flex; flex-direction: column; min-width: 180px; padding: 8px 6px 0; gap: 2px; }

  .nav-item {
    display: flex; align-items: center; gap: 10px;
    height: 40px; padding: 0 12px;
    margin: 0 2px;
    color: var(--text-muted); text-decoration: none; white-space: nowrap;
    border-radius: var(--radius-pill);
  }
  .nav-item:hover { background: var(--surface-hover); color: var(--text); }
  .nav-item.active { color: var(--accent-contrast); background: var(--accent); }

  .nav-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; line-height: 1; }
  .nav-label { font-size: 12px; font-weight: 500; }

  .nav-separator { border: none; border-top: 1px solid var(--border); margin: 8px 10px; }

  @media (max-width: 600px) {
    .nav {
      position: fixed;
      top: 48px; bottom: 0; left: 0;
      width: 0;
    }
    .nav.expanded { width: 200px; }
  }
</style>
