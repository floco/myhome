<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createPropertiesStore } from "../propertiesStore.svelte";
  import Card from "./ui/Card.svelte";

  type PropertiesStore = ReturnType<typeof createPropertiesStore>;

  interface Props {
    propertiesStore: PropertiesStore;
    onnavigate: () => void;
  }
  let { propertiesStore, onnavigate }: Props = $props();

  const STATUSES = ["watching", "visited", "proposal_made", "purchased", "rejected"] as const;

  function countByStatus(status: string): number {
    return propertiesStore.properties.filter((p) => p.status === status).length;
  }

  function statusLabel(status: string): string {
    const map: Record<string, string> = {
      watching: "properties.status.watching",
      visited: "properties.status.visited",
      proposal_made: "home.properties.statusProposal",
      purchased: "properties.status.purchased",
      rejected: "properties.status.rejected",
    };
    return $_(map[status] ?? status);
  }

  function statusColor(status: string): string {
    if (status === "purchased") return "#33aa66";
    if (status === "rejected") return "#cc3333";
    if (status === "proposal_made") return "#cc8833";
    if (status === "visited") return "#3388cc";
    return "#888888";
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  const recent = $derived(propertiesStore.properties.slice(-3).reverse());
</script>

{#if propertiesStore.properties.length > 0}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div
    class="widget"
    role="button"
    tabindex="0"
    onclick={onnavigate}
    onkeydown={(e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onnavigate();
      }
    }}
  >
    <Card>
      <div class="header"><h3>🏘 {$_('common.modules.properties')}</h3></div>
      <div class="status-counts">
        {#each STATUSES as s}
          <span class="status-count" style="color:{statusColor(s)}">{statusLabel(s)} {countByStatus(s)}</span>
        {/each}
      </div>
      <ul class="recent-list">
        {#each recent as p (p.id)}
          <li>
            <span class="emoji">{p.emoji}</span>
            <span class="name">{p.name}</span>
            <span class="price">{p.price != null ? fmt(p.price) + " €" : "—"}</span>
          </li>
        {/each}
      </ul>
    </Card>
  </div>
{/if}

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .status-counts { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
  .recent-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .recent-list li { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-muted); }
  .recent-list .name { flex: 1; color: var(--text); font-weight: 500; }
  .recent-list .price { font-weight: 600; }
</style>
