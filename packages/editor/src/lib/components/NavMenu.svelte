<script lang="ts">
  interface Props {
    currentRoute: string;
    expanded: boolean;
    onclose: () => void;
  }
  let { currentRoute, expanded, onclose }: Props = $props();

  const modules = [
    { href: "#/",            icon: "🏠", label: "Floor Plan"   },
    { href: "#/chores",      icon: "✅", label: "Chores"       },
    { href: "#/inventory",   icon: "📦", label: "Inventory"    },
    { href: "#/consumables", icon: "🛒", label: "Consumables"  },
    { href: "#/works",       icon: "🔧", label: "Works"        },
    { href: "#/finance",     icon: "💶", label: "Finance"      },
  ];

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

  .nav-body { flex: 1; display: flex; flex-direction: column; min-width: 180px; padding-top: 6px; }

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
