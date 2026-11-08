<!-- packages/editor/src/lib/components/PropertySuggestionsTab.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createPropertySearchStore, PropertySuggestion } from "../propertySearchStore.svelte";
  import Button from "./ui/Button.svelte";
  import FilterButton from "./ui/FilterButton.svelte";
  import Modal from "./ui/Modal.svelte";

  type SearchStore = ReturnType<typeof createPropertySearchStore>;

  interface Props {
    searchStore: SearchStore;
    onaccepted?: () => void;
    onopensearches: () => void;
  }

  let { searchStore, onaccepted, onopensearches }: Props = $props();

  let searchFilter = $state("");
  let filterModalOpen = $state(false);
  let actionError = $state<string | null>(null);
  let busyId = $state<string | null>(null);
  let brokenImages = $state<Record<string, boolean>>({});

  const searchNames = $derived(new Map(searchStore.searches.map((s) => [s.id, s.name])));
  const visible = $derived(
    searchStore.suggestions.filter((g) => !searchFilter || g.searchId === searchFilter),
  );

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function typeLabel(type: PropertySuggestion["type"]): string {
    if (type === "land") return $_("properties.type.land");
    if (type === "new_build") return $_("properties.type.newBuild");
    if (type === "house") return $_("properties.type.house");
    return "";
  }

  function facts(g: PropertySuggestion): string[] {
    const out: string[] = [];
    const t = typeLabel(g.type);
    if (t) out.push(t);
    if (g.price != null) out.push(`${fmt(g.price)} ${g.currency ?? "€"}`);
    if (g.landSize != null) out.push($_("properties.page.landSize", { values: { size: fmt(g.landSize) } }));
    if (g.builtSize != null) out.push($_("properties.page.builtSize", { values: { size: fmt(g.builtSize) } }));
    if (g.location) out.push(g.location);
    return out;
  }

  function when(iso: string | null): string {
    if (!iso) return "";
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
  }

  function day(iso: string): string {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
  }

  async function act(id: string, fn: () => Promise<unknown>): Promise<void> {
    busyId = id;
    actionError = null;
    try {
      await fn();
    } catch (e) {
      actionError = $_("propertySearch.inbox.actionError", { values: { error: e instanceof Error ? e.message : String(e) } });
    } finally {
      busyId = null;
    }
  }

  function accept(id: string) {
    return act(id, async () => {
      await searchStore.accept(id);
      onaccepted?.();
    });
  }
</script>

<div class="suggestions">
  <div class="toolbar">
    <span class="spacer"></span>
    <FilterButton active={searchFilter !== ""} title={$_("common.filters")} onclick={() => { filterModalOpen = true; }} />
    <Button variant="secondary" onclick={onopensearches}>🔎 {$_("propertySearch.inbox.searches")}</Button>
  </div>

  <Modal open={filterModalOpen} title={$_("common.filters")} onclose={() => { filterModalOpen = false; }} width="360px">
    <label class="field">
      <span>{$_("propertySearch.inbox.filterSearch")}</span>
      <select class="native-input" bind:value={searchFilter} data-testid="search-filter">
        <option value="">{$_("propertySearch.inbox.allSearches")}</option>
        {#each searchStore.searches as s (s.id)}
          <option value={s.id}>{s.name}</option>
        {/each}
      </select>
    </label>
  </Modal>

  {#if searchStore.searches.length > 0}
    <div class="runs">
      {#each searchStore.searches as s (s.id)}
        <div class="run-line" class:run-error={s.lastRunStatus === "failed" || s.lastRunStatus === "usage_limited"}>
          <strong>{s.name}</strong> —
          {#if s.lastRunAt && s.lastRunStatus}
            {$_("propertySearch.inbox.lastRun", { values: { when: when(s.lastRunAt), status: $_(`propertySearch.status.${s.lastRunStatus}`) } })}
            {#if s.lastRunNew != null}
              · {$_("propertySearch.inbox.lastRunCounts", { values: { new: s.lastRunNew, dup: s.lastRunDuplicates ?? 0 } })}
            {/if}
            {#if s.lastRunError}<span class="err">({s.lastRunError})</span>{/if}
            {#if s.lastRunEmailError}
              <span class="err email-err">{$_("propertySearch.inbox.emailFailed", { values: { error: s.lastRunEmailError } })}</span>
            {/if}
          {:else}
            {$_("propertySearch.inbox.neverRun")}
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  {#if actionError}<div class="action-error" role="alert">{actionError}</div>{/if}

  <div class="list">
    {#if visible.length === 0}
      <div class="empty">
        {searchStore.searches.length === 0 ? $_("propertySearch.inbox.emptyNoSearch") : $_("propertySearch.inbox.empty")}
      </div>
    {:else}
      {#each visible as g (g.id)}
        <article class="card" class:pinned={g.status === "pinned"} data-testid="suggestion">
          {#if g.imageUrl && !brokenImages[g.id]}
            <img class="thumb" src={g.imageUrl} alt="" loading="lazy" referrerpolicy="no-referrer"
              onerror={() => { brokenImages = { ...brokenImages, [g.id]: true }; }} />
          {/if}
          <div class="body">
            <div class="title-row">
              {#if g.status === "pinned"}<span class="pin" title={$_("propertySearch.inbox.pinned")}>📌</span>{/if}
              <a class="title" href={g.listingUrl} target="_blank" rel="noopener noreferrer">{g.title}</a>
            </div>
            <div class="facts">{facts(g).join(" · ")}</div>
            {#if g.reason}<p class="reason">{g.reason}</p>{/if}
            <div class="meta">
              {g.sourceSite}
              {#if g.publishedAt} · {$_("propertySearch.inbox.published", { values: { date: day(g.publishedAt) } })}{/if}
              {#if searchNames.get(g.searchId)} · {searchNames.get(g.searchId)}{/if}
            </div>
          </div>
          <div class="actions">
            <Button iconOnly variant="success" disabled={busyId === g.id} title={$_("propertySearch.inbox.accept")} onclick={() => accept(g.id)}>✓</Button>
            <Button iconOnly variant="ghost" disabled={busyId === g.id}
              title={g.status === "pinned" ? $_("propertySearch.inbox.unpin") : $_("propertySearch.inbox.pin")}
              onclick={() => act(g.id, () => searchStore.togglePin(g.id))}>📌</Button>
            <Button iconOnly variant="danger" disabled={busyId === g.id} title={$_("propertySearch.inbox.reject")} onclick={() => act(g.id, () => searchStore.reject(g.id))}>✕</Button>
          </div>
        </article>
      {/each}
    {/if}
  </div>
</div>

<style>
  .suggestions { display: flex; flex-direction: column; flex: 1; min-height: 0; }
  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .spacer { flex: 1; }
  .field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-muted); }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .runs { padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--border); font-size: 11px; color: var(--text-faint); display: flex; flex-direction: column; gap: 2px; }
  .run-line strong { color: var(--text-muted); font-weight: 600; }
  .run-error { color: var(--danger, #cc3333); }
  .err { margin-left: 4px; }
  .email-err { color: var(--danger, #cc3333); }
  .action-error { margin: var(--space-2) var(--space-3) 0; font-size: 12px; color: var(--danger, #cc3333); }
  .list { flex: 1; overflow-y: auto; padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-3); }
  .empty { padding: 32px; text-align: center; color: var(--text-faint); font-size: 13px; }
  .card {
    display: flex; gap: var(--space-3); padding: var(--space-3); border: 1px solid var(--border);
    border-radius: var(--radius-md); background: var(--surface); box-sizing: border-box; min-width: 0;
  }
  .card.pinned { border-color: var(--accent); }
  .thumb { width: 96px; height: 72px; object-fit: cover; border-radius: var(--radius-sm); flex-shrink: 0; }
  .body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
  .title-row { display: flex; gap: 4px; align-items: baseline; min-width: 0; }
  .title { color: var(--text); font-weight: 600; font-size: 13px; text-decoration: none; overflow-wrap: anywhere; }
  .title:hover { text-decoration: underline; }
  .facts { font-size: 12px; color: var(--text-muted); }
  .reason { margin: 0; font-size: 12px; color: var(--text); line-height: 1.4; }
  .meta { font-size: 11px; color: var(--text-faint); overflow-wrap: anywhere; }
  .actions { display: flex; flex-direction: column; gap: 4px; flex-shrink: 0; }
  @media (max-width: 700px) {
    .card { flex-wrap: wrap; }
    .thumb { width: 100%; height: 140px; }
    .actions { flex-direction: row; width: 100%; justify-content: flex-end; }
  }
</style>
