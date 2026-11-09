<!-- packages/editor/src/lib/components/settings/SettingsPropertySearch.svelte -->
<script lang="ts">
  import { onMount } from "svelte";
  import { _ } from "svelte-i18n";
  import type { createPropertySearchStore, PropertySearchConfig, PropertySearchConfigPatch, SearchLanguage } from "../../propertySearchStore.svelte";
  import Button from "../ui/Button.svelte";
  import Card from "../ui/Card.svelte";

  type SearchStore = Pick<ReturnType<typeof createPropertySearchStore>, "loadConfig" | "saveConfig" | "sendTestEmail">;

  interface Props {
    searchStore: SearchStore;
  }
  let { searchStore }: Props = $props();

  const RUNNER_REPO = "https://github.com/floco/property-search-runner";

  let loaded = $state(false);
  let keySet = $state(false);
  let retentionStr = $state("30");
  let apiKey = $state("");
  let senderEmail = $state("");
  let senderName = $state("");
  let recipientsText = $state("");
  let appBaseUrl = $state("");
  let language = $state<SearchLanguage>("en");
  let saving = $state(false);
  let status = $state<{ kind: "ok" | "error"; text: string } | null>(null);

  function apply(cfg: PropertySearchConfig) {
    keySet = cfg.brevoApiKeySet;
    retentionStr = String(cfg.retentionDays);
    senderEmail = cfg.senderEmail;
    senderName = cfg.senderName;
    recipientsText = cfg.recipients.join("\n");
    appBaseUrl = cfg.appBaseUrl;
    language = cfg.language ?? "en";
  }

  function errText(e: unknown): string {
    return $_("propertySearch.settings.error", { values: { error: e instanceof Error ? e.message : String(e) } });
  }

  onMount(async () => {
    try {
      apply(await searchStore.loadConfig());
    } catch (e) {
      status = { kind: "error", text: errText(e) };
    } finally {
      loaded = true;
    }
  });

  async function save() {
    saving = true;
    status = null;
    const patch: PropertySearchConfigPatch = {
      retentionDays: parseInt(retentionStr, 10) || 30,
      senderEmail: senderEmail.trim(),
      senderName: senderName.trim(),
      recipients: recipientsText.split(/[\n,;]/).map((r) => r.trim()).filter(Boolean),
      appBaseUrl: appBaseUrl.trim(),
      language,
    };
    if (apiKey.trim()) patch.brevoApiKey = apiKey.trim();
    try {
      apply(await searchStore.saveConfig(patch));
      apiKey = "";
      status = { kind: "ok", text: $_("propertySearch.settings.saved") };
    } catch (e) {
      status = { kind: "error", text: errText(e) };
    } finally {
      saving = false;
    }
  }

  async function testEmail() {
    status = null;
    try {
      await searchStore.sendTestEmail();
      status = { kind: "ok", text: $_("propertySearch.settings.testSent") };
    } catch (e) {
      status = { kind: "error", text: errText(e) };
    }
  }
</script>

<Card>
  <div class="section-header"><h2>{$_("propertySearch.settings.title")}</h2></div>
  <p class="section-desc">{$_("propertySearch.settings.intro")}</p>

  <div class="form" class:dim={!loaded}>
    <label class="field">
      <span class="label">{$_("propertySearch.settings.retentionDays")}</span>
      <input class="native-input narrow" type="number" min="1" max="3650" data-testid="ps-retention" bind:value={retentionStr} />
      <span class="hint">{$_("propertySearch.settings.retentionHelp")}</span>
    </label>

    <label class="field">
      <span class="label">{$_("propertySearch.settings.language")}</span>
      <select class="native-input narrow-select" data-testid="ps-language" bind:value={language}>
        <option value="en">English</option>
        <option value="fr">Français</option>
      </select>
      <span class="hint">{$_("propertySearch.settings.languageHelp")}</span>
    </label>

    <h3>{$_("propertySearch.settings.email")}</h3>
    <label class="field">
      <span class="label">{$_("propertySearch.settings.brevoApiKey")}</span>
      <input class="native-input" type="password" autocomplete="off" data-testid="ps-key" bind:value={apiKey}
        placeholder={keySet ? $_("propertySearch.settings.brevoKeySet") : "xkeysib-…"} />
    </label>
    <div class="row">
      <label class="field">
        <span class="label">{$_("propertySearch.settings.senderEmail")}</span>
        <input class="native-input" type="email" data-testid="ps-sender" bind:value={senderEmail} />
      </label>
      <label class="field">
        <span class="label">{$_("propertySearch.settings.senderName")}</span>
        <input class="native-input" data-testid="ps-sender-name" bind:value={senderName} />
      </label>
    </div>
    <label class="field">
      <span class="label">{$_("propertySearch.settings.recipients")}</span>
      <textarea class="native-input" rows="3" data-testid="ps-recipients" bind:value={recipientsText}></textarea>
    </label>
    <label class="field">
      <span class="label">{$_("propertySearch.settings.appBaseUrl")}</span>
      <input class="native-input" type="url" placeholder="http://homeassistant.local:8000" data-testid="ps-base-url" bind:value={appBaseUrl} />
    </label>

    <div class="actions">
      <Button variant="secondary" onclick={testEmail}><span data-testid="ps-test">{$_("propertySearch.settings.testEmail")}</span></Button>
      <Button variant="primary" disabled={saving || !loaded} onclick={save}><span data-testid="ps-save">{$_("propertySearch.settings.save")}</span></Button>
    </div>
    {#if status}
      <div class={status.kind === "ok" ? "ok" : "error"} role={status.kind === "error" ? "alert" : "status"}>{status.text}</div>
    {/if}
  </div>
</Card>

<Card>
  <div class="section-header"><h2>{$_("propertySearch.settings.runnerTitle")}</h2></div>
  <p class="section-desc">{$_("propertySearch.settings.runnerHelp")}</p>
  <a href={RUNNER_REPO} target="_blank" rel="noopener noreferrer">{$_("propertySearch.settings.runnerLink")} ↗</a>
</Card>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  h3 { margin: var(--space-2) 0 0; font-size: 12px; color: var(--text-muted); font-weight: 600; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; overflow-wrap: anywhere; }
  .form { display: flex; flex-direction: column; gap: var(--space-3); }
  .form.dim { opacity: 0.6; }
  .row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--space-3); }
  .field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
  .label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .hint { font-size: 11px; color: var(--text-faint); }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input.narrow { max-width: 140px; }
  .native-input.narrow-select { max-width: 220px; }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .actions { display: flex; gap: var(--space-2); justify-content: flex-end; flex-wrap: wrap; }
  .ok { color: var(--success, #33aa66); font-size: 12px; }
  .error { color: var(--danger); font-size: 12px; overflow-wrap: anywhere; }
  a { color: var(--accent); font-size: 13px; }
</style>
