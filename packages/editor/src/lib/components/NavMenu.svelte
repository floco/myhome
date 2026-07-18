<script lang="ts">
  import { homesStore } from "../homesStore.svelte";

  interface Props {
    currentRoute: string;
    expanded: boolean;
    onclose: () => void;
  }
  let { currentRoute, expanded, onclose }: Props = $props();

  const ALL_MODULES = [
    { id: "home",        href: "#/",            icon: "🏡", label: "Home"             },
    { id: "plan",        href: "#/plan",        icon: "📐", label: "Floor Plan"       },
    { id: "chores",      href: "#/chores",      icon: "✅", label: "Chores"           },
    { id: "inventory",   href: "#/inventory",   icon: "📦", label: "Inventory"        },
    { id: "consumables", href: "#/consumables", icon: "🛒", label: "Consumables"      },
    { id: "works",       href: "#/works",       icon: "🔧", label: "Works"            },
    { id: "kb",          href: "#/kb",          icon: "📖", label: "Knowledge Base"   },
    { id: "costs",       href: "#/costs",       icon: "💶", label: "Costs"            },
    { id: "locations",   href: "#/locations",   icon: "🌍", label: "Locations"   },
    { id: "properties",  href: "#/properties",  icon: "🏘", label: "Properties",  placeholder: true },
    { id: "budget",      href: "#/budget",      icon: "💰", label: "Budget",      placeholder: true },
    { id: "visits",      href: "#/visits",      icon: "📅", label: "Visits",      placeholder: true },
    { id: "contacts",    href: "#/contacts",    icon: "👤", label: "Contacts",    placeholder: true },
    { id: "checklist",   href: "#/checklist",   icon: "✅", label: "Checklist",   placeholder: true },
  ];

  const visibleModules = $derived(
    ALL_MODULES.filter((m) => homesStore.activeHome?.enabledModules.includes(m.id) ?? true)
  );

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
    {#each visibleModules as mod (mod.id)}
      <a
        href={mod.href}
        class="nav-item"
        class:active={isActive(mod.href)}
        class:soon={mod.placeholder}
        title={mod.placeholder ? `${mod.label} — coming soon` : mod.label}
        onclick={onclose}
      >
        <span class="nav-icon">{mod.icon}</span>
        <span class="nav-label">{mod.label}{#if mod.placeholder && expanded}<span class="soon-badge">Soon</span>{/if}</span>
      </a>
    {/each}
    <hr class="nav-separator" />
    <a href={settingsLink.href} class="nav-item" class:active={isActive(settingsLink.href)} title={settingsLink.label} onclick={onclose}>
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
  .nav-item.soon { opacity: 0.55; }

  .nav-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; line-height: 1; }
  .nav-label { font-size: 12px; font-weight: 500; }

  .soon-badge {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: var(--surface-hover);
    color: var(--text-muted);
    border-radius: var(--radius-pill);
    padding: 1px 5px;
    margin-left: 4px;
  }

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
