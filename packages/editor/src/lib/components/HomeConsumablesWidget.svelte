<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createConsumableStore } from "../consumableStore.svelte";
  import { stockStatus } from "../consumableStore.svelte";
  import Card from "./ui/Card.svelte";

  type ConsumableStore = ReturnType<typeof createConsumableStore>;

  interface Props {
    consumableStore: ConsumableStore;
    onnavigate: () => void;
  }

  let { consumableStore, onnavigate }: Props = $props();

  const alertItems = $derived(
    consumableStore.consumables.filter((c) => {
      const s = stockStatus(c);
      return s === "low" || s === "empty";
    }),
  );

  const emptyCount = $derived(
    alertItems.filter((c) => stockStatus(c) === "empty").length,
  );
  const lowCount = $derived(
    alertItems.filter((c) => stockStatus(c) === "low").length,
  );

  const STATE_COLOR: Record<string, string> = {
    ok: "#4caf50",
    low: "#ff9800",
    empty: "#f44336",
  };
</script>

{#if alertItems.length > 0}
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
      <div class="header">
        <h3>🛒 {$_('common.modules.consumables')}</h3>
      </div>
      <div class="pills">
        {#if emptyCount > 0}
          <span class="pill empty">{$_('home.consumables.emptyPill', { values: { n: emptyCount } })}</span>
        {/if}
        {#if lowCount > 0}
          <span class="pill low">{$_('home.consumables.lowPill', { values: { n: lowCount } })}</span>
        {/if}
      </div>
      <ul class="item-list">
        {#each alertItems as c (c.id)}
          {@const st = stockStatus(c)}
          <li>
            <span class="item-emoji">{c.emoji}</span>
            <span class="item-name">{c.name}</span>
            <span class="item-qty" style="color:{STATE_COLOR[st]}">{c.quantity} {c.unit}</span>
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
  .pills { display: flex; gap: 6px; margin-bottom: var(--space-2); }
  .pill { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 10px; letter-spacing: 0.04em; }
  .pill.empty { background: #33100f; color: #f44336; }
  .pill.low { background: #332610; color: #ff9800; }
  .item-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .item-list li { display: flex; align-items: center; gap: 6px; font-size: 12px; }
  .item-emoji { font-size: 14px; }
  .item-name { flex: 1; color: var(--text-muted); }
  .item-qty { font-weight: 600; font-size: 11px; }
</style>
