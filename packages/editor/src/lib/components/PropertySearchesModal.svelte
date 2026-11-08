<!-- packages/editor/src/lib/components/PropertySearchesModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type {
    createPropertySearchStore,
    PropertySearch,
    PropertySearchInput,
    SearchFrequency,
  } from "../propertySearchStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Button from "./ui/Button.svelte";

  type SearchStore = ReturnType<typeof createPropertySearchStore>;

  interface Props {
    open: boolean;
    searchStore: SearchStore;
    onclose: () => void;
  }

  let { open, searchStore, onclose }: Props = $props();

  const DEFAULTS: PropertySearchInput = {
    name: "", prompt: "", enabled: true, frequency: "daily", time: "08:00",
    dayOfWeek: 1, dayOfMonth: 1, maxResultsPerRun: 10, maxListingAgeDays: 7,
  };

  // null = list view; "new" = create form; otherwise the id being edited.
  let editing = $state<string | null>(null);
  let form = $state<PropertySearchInput>({ ...DEFAULTS });
  let confirmDeleteId = $state<string | null>(null);
  let queuedId = $state<string | null>(null);
  let error = $state<string | null>(null);
  let saving = $state(false);

  const canSave = $derived(form.name.trim() !== "" && form.prompt.trim() !== "" && /^\d{2}:\d{2}$/.test(form.time));

  function startNew() {
    form = { ...DEFAULTS };
    editing = "new";
    error = null;
  }

  function startEdit(s: PropertySearch) {
    form = {
      name: s.name, prompt: s.prompt, enabled: s.enabled, frequency: s.frequency, time: s.time,
      dayOfWeek: s.dayOfWeek, dayOfMonth: s.dayOfMonth, maxResultsPerRun: s.maxResultsPerRun,
      maxListingAgeDays: s.maxListingAgeDays,
    };
    editing = s.id;
    error = null;
  }

  function schedule(s: PropertySearch): string {
    if (s.frequency === "weekly") {
      return $_("propertySearch.searches.scheduleWeekly", { values: { day: $_(`propertySearch.searches.day${s.dayOfWeek}`), time: s.time } });
    }
    if (s.frequency === "monthly") {
      return $_("propertySearch.searches.scheduleMonthly", { values: { day: s.dayOfMonth, time: s.time } });
    }
    return $_("propertySearch.searches.scheduleDaily", { values: { time: s.time } });
  }

  async function guarded(fn: () => Promise<void>) {
    error = null;
    try {
      await fn();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  async function save() {
    if (!canSave) return;
    saving = true;
    const data: PropertySearchInput = {
      ...form, name: form.name.trim(), prompt: form.prompt.trim(),
      maxResultsPerRun: Number(form.maxResultsPerRun), maxListingAgeDays: Number(form.maxListingAgeDays),
      dayOfWeek: Number(form.dayOfWeek), dayOfMonth: Number(form.dayOfMonth),
    };
    await guarded(async () => {
      if (editing === "new") await searchStore.createSearch(data);
      else if (editing) await searchStore.updateSearch(editing, data);
      editing = null;
    });
    saving = false;
  }

  function runNow(id: string) {
    return guarded(async () => {
      await searchStore.runNow(id);
      queuedId = id;
    });
  }

  function remove(id: string) {
    return guarded(async () => {
      await searchStore.deleteSearch(id);
      confirmDeleteId = null;
    });
  }

  function toggle(s: PropertySearch) {
    return guarded(() => searchStore.updateSearch(s.id, { enabled: !s.enabled }));
  }

  function close() {
    editing = null;
    confirmDeleteId = null;
    queuedId = null;
    onclose();
  }
</script>

<Modal {open} title={editing === null ? $_("propertySearch.searches.title") : editing === "new" ? $_("propertySearch.searches.new") : $_("propertySearch.searches.edit")} onclose={close} width="560px">
  {#if error}<div class="error" role="alert">{error}</div>{/if}

  {#if editing === null}
    <div class="list">
      {#if searchStore.searches.length === 0}
        <p class="empty">{$_("propertySearch.searches.empty")}</p>
      {/if}
      {#each searchStore.searches as s (s.id)}
        <div class="row" class:paused={!s.enabled}>
          <div class="info">
            <div class="name">{s.name}</div>
            <div class="sub">{schedule(s)}{s.enabled ? "" : ` · ${$_("propertySearch.searches.paused")}`}</div>
            {#if queuedId === s.id || s.runRequestedAt}<div class="queued">{$_("propertySearch.searches.queued")}</div>{/if}
          </div>
          <div class="row-actions">
            {#if confirmDeleteId === s.id}
              <span class="confirm-text">{$_("propertySearch.searches.confirmDelete", { values: { name: s.name } })}</span>
              <Button variant="danger" onclick={() => remove(s.id)}><span data-testid="confirm-delete-{s.id}">✓</span></Button>
              <Button variant="ghost" onclick={() => { confirmDeleteId = null; }}>✕</Button>
            {:else}
              <label class="toggle" title={$_("propertySearch.searches.enabled")}>
                <input type="checkbox" checked={s.enabled} data-testid="toggle-{s.id}" onclick={(e) => { e.preventDefault(); toggle(s); }} />
              </label>
              <Button iconOnly variant="ghost" title={$_("propertySearch.searches.runNow")} onclick={() => runNow(s.id)}><span data-testid="run-{s.id}">▶</span></Button>
              <Button iconOnly variant="ghost" title={$_("propertySearch.searches.edit_")} onclick={() => startEdit(s)}><span data-testid="edit-{s.id}">✎</span></Button>
              <Button iconOnly variant="ghost" title={$_("propertySearch.searches.delete")} onclick={() => { confirmDeleteId = s.id; }}><span data-testid="delete-{s.id}">🗑</span></Button>
            {/if}
          </div>
        </div>
      {/each}
      <div class="list-footer">
        <Button variant="primary" onclick={startNew}><span data-testid="new-search">＋ {$_("propertySearch.searches.new")}</span></Button>
      </div>
    </div>
  {:else}
    <div class="form">
      <label class="field">
        <span>{$_("propertySearch.searches.name")} *</span>
        <input class="native-input" data-testid="search-name" bind:value={form.name} />
      </label>
      <label class="field">
        <span>{$_("propertySearch.searches.prompt")} *</span>
        <textarea class="native-input" rows="6" data-testid="search-prompt" bind:value={form.prompt}
          placeholder={$_("propertySearch.searches.promptPlaceholder")}></textarea>
      </label>
      <div class="grid">
        <label class="field">
          <span>{$_("propertySearch.searches.frequency")}</span>
          <select class="native-input" data-testid="search-frequency" bind:value={form.frequency}>
            {#each ["daily", "weekly", "monthly"] as f (f)}
              <option value={f}>{$_(`propertySearch.searches.${f as SearchFrequency}`)}</option>
            {/each}
          </select>
        </label>
        <label class="field">
          <span>{$_("propertySearch.searches.time")}</span>
          <input class="native-input" type="time" data-testid="search-time" bind:value={form.time} />
        </label>
        {#if form.frequency === "weekly"}
          <label class="field">
            <span>{$_("propertySearch.searches.dayOfWeek")}</span>
            <select class="native-input" data-testid="search-dow" bind:value={form.dayOfWeek}>
              {#each [1, 2, 3, 4, 5, 6, 7] as d (d)}
                <option value={d}>{$_(`propertySearch.searches.day${d}`)}</option>
              {/each}
            </select>
          </label>
        {:else if form.frequency === "monthly"}
          <label class="field">
            <span>{$_("propertySearch.searches.dayOfMonth")}</span>
            <input class="native-input" type="number" min="1" max="31" data-testid="search-dom" bind:value={form.dayOfMonth} />
          </label>
        {/if}
        <label class="field">
          <span>{$_("propertySearch.searches.maxResults")}</span>
          <input class="native-input" type="number" min="1" max="50" data-testid="search-max-results" bind:value={form.maxResultsPerRun} />
        </label>
        <label class="field">
          <span>{$_("propertySearch.searches.maxAge")}</span>
          <input class="native-input" type="number" min="1" max="365" data-testid="search-max-age" bind:value={form.maxListingAgeDays} />
        </label>
      </div>
      <label class="check">
        <input type="checkbox" bind:checked={form.enabled} />
        {$_("propertySearch.searches.enabled")}
      </label>
      <div class="form-actions">
        <Button variant="ghost" onclick={() => { editing = null; }}>{$_("propertySearch.searches.cancel")}</Button>
        <Button variant="primary" disabled={!canSave || saving} onclick={save}><span data-testid="search-save">{$_("propertySearch.searches.save")}</span></Button>
      </div>
    </div>
  {/if}
</Modal>

<style>
  .error { color: var(--danger, #cc3333); font-size: 12px; margin-bottom: var(--space-2); }
  .empty { color: var(--text-faint); font-size: 13px; margin: 0 0 var(--space-3); }
  .list { display: flex; flex-direction: column; gap: var(--space-2); }
  .row {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2);
    border: 1px solid var(--border); border-radius: var(--radius-md); min-width: 0;
  }
  .row.paused { opacity: 0.65; }
  .info { flex: 1; min-width: 0; }
  .name { font-weight: 600; font-size: 13px; color: var(--text); overflow-wrap: anywhere; }
  .sub { font-size: 11px; color: var(--text-faint); }
  .queued { font-size: 11px; color: var(--accent); margin-top: 2px; }
  .row-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }
  .confirm-text { font-size: 11px; color: var(--text-muted); max-width: 180px; }
  .toggle { display: flex; align-items: center; padding: 0 4px; cursor: pointer; }
  .list-footer { display: flex; justify-content: flex-end; margin-top: var(--space-2); }
  .form { display: flex; flex-direction: column; gap: var(--space-3); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-muted); min-width: 0; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  textarea.native-input { resize: vertical; line-height: 1.4; }
  .check { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text); }
  .form-actions { display: flex; justify-content: flex-end; gap: var(--space-2); }
</style>
