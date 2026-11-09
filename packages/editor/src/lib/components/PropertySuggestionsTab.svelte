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

  type SortKey = "priceAsc" | "priceDesc" | "search";

  let searchFilter = $state("");
  let sortKey = $state<SortKey>("priceAsc");
  let filterModalOpen = $state(false);
  let actionError = $state<string | null>(null);
  let busyId = $state<string | null>(null);
  let brokenImages = $state<Record<string, boolean>>({});

  const searchNames = $derived(new Map(searchStore.searches.map((s) => [s.id, s.name])));
  // Unknown prices always sink to the bottom, whichever direction.
  function byPrice(a: PropertySuggestion, b: PropertySuggestion, dir: 1 | -1): number {
    if (a.price == null || b.price == null) return a.price == null ? (b.price == null ? 0 : 1) : -1;
    return (a.price - b.price) * dir;
  }

  function compare(a: PropertySuggestion, b: PropertySuggestion): number {
    if (sortKey === "priceDesc") return byPrice(a, b, -1);
    if (sortKey === "search") {
      const byName = (searchNames.get(a.searchId) ?? "").localeCompare(searchNames.get(b.searchId) ?? "");
      if (byName !== 0) return byName;
    }
    return byPrice(a, b, 1);
  }

  const visible = $derived(
    searchStore.suggestions.filter((g) => !searchFilter || g.searchId === searchFilter).sort(compare),
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
    if (g.landSize != null) out.push($_("properties.page.landSize", { values: { size: fmt(g.landSize) } }));
    if (g.builtSize != null) out.push($_("properties.page.builtSize", { values: { size: fmt(g.builtSize) } }));
    // Show the full location only when the city tag doesn't already carry it.
    if (g.location && g.location !== place(g).city) out.push(g.location);
    return out;
  }

  // Older suggestions only have a free-text "town, region, country" location.
  function place(g: PropertySuggestion): { city: string; country: string } {
    const parts = (g.location ?? "").split(",").map((p) => p.trim()).filter(Boolean);
    return {
      city: g.city || parts[0] || "",
      country: g.country || (parts.length >= 2 ? parts[parts.length - 1] : ""),
    };
  }

  function tags(g: PropertySuggestion): { kind: "price" | "country" | "city"; text: string }[] {
    const out: { kind: "price" | "country" | "city"; text: string }[] = [];
    if (g.price != null) out.push({ kind: "price", text: `${fmt(g.price)} ${g.currency ?? "€"}` });
    const { city, country } = place(g);
    if (country) out.push({ kind: "country", text: country });
    if (city) out.push({ kind: "city", text: city });
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
    <label class="sort">
      <span>{$_("propertySearch.inbox.sortBy")}</span>
      <select class="native-input sort-select" bind:value={sortKey} data-testid="suggestion-sort">
        <option value="priceAsc">{$_("propertySearch.inbox.sortPriceAsc")}</option>
        <option value="priceDesc">{$_("propertySearch.inbox.sortPriceDesc")}</option>
        <option value="search">{$_("propertySearch.inbox.sortSearch")}</option>
      </select>
    </label>
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
            {#if tags(g).length > 0}
              <div class="tags">
                {#each tags(g) as tag (tag.kind)}
                  <span class="tag tag-{tag.kind}" data-tag={tag.kind}>{tag.text}</span>
                {/each}
              </div>
            {/if}
            <div class="title-row">
              {#if g.status === "pinned"}<span class="pin" title={$_("propertySearch.inbox.pinned")}>📌</span>{/if}
              <a class="title" href={g.listingUrl} target="_blank" rel="noopener noreferrer">{g.title}</a>
            </div>
            {#if facts(g).length > 0}<div class="facts">{facts(g).join(" · ")}</div>{/if}
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
  .sort { display: flex; align-items: center; gap: var(--space-2); font-size: 12px; color: var(--text-muted); min-width: 0; flex: 0 1 auto; }
  .sort-select { width: auto; min-width: 0; max-width: 100%; padding: 6px 10px; }
  .toolbar > :global(button) { flex-shrink: 0; white-space: nowrap; }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag {
    display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 999px;
    font-size: 14px; font-weight: 600; line-height: 1.3; border: 1px solid var(--border);
    background: var(--surface-alt); color: var(--text); overflow-wrap: anywhere;
  }
  .tag-price { background: var(--accent); border-color: var(--accent); color: var(--accent-contrast, #fff); }
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
    .sort > span { display: none; }
    .card { flex-wrap: wrap; }
    .thumb { width: 100%; height: 140px; }
    .actions { flex-direction: row; width: 100%; justify-content: flex-end; }
  }
</style>
