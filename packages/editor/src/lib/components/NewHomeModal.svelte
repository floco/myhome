<script lang="ts">
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import { homesStore } from "../homesStore.svelte";

  interface Props {
    open: boolean;
    onclose: () => void;
    /** If true, hides the cancel button (zero-homes first-time flow) */
    required?: boolean;
  }
  let { open, onclose, required = false }: Props = $props();

  let name = $state("");
  let type = $state<"existing" | "project">("existing");
  let saving = $state(false);
  let error = $state<string | null>(null);

  async function submit(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true;
    error = null;
    try {
      await homesStore.createHome(name.trim(), type);
      name = "";
      type = "existing";
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to create home";
    } finally {
      saving = false;
    }
  }
</script>

<Modal {open} title="New home" onclose={required ? undefined : onclose}>
  <div class="form">
    <Input label="Name" bind:value={name} placeholder="Rue des Lilas" />

    <fieldset class="type-group">
      <legend>Type</legend>
      <label class="type-option" class:selected={type === "existing"}>
        <input type="radio" bind:group={type} value="existing" />
        <span class="type-icon">🏠</span>
        <span class="type-body">
          <strong>Existing home</strong>
          <small>A property you already own or live in — full module set.</small>
        </span>
      </label>
      <label class="type-option" class:selected={type === "project"}>
        <input type="radio" bind:group={type} value="project" />
        <span class="type-icon">🏗</span>
        <span class="type-body">
          <strong>Project home</strong>
          <small>Scouting locations, searching for land, or managing a build.</small>
        </span>
      </label>
    </fieldset>

    {#if error}
      <p class="error">{error}</p>
    {/if}
  </div>

  {#snippet footer()}
    {#if !required}
      <Button variant="ghost" onclick={onclose} disabled={saving}>Cancel</Button>
    {/if}
    <Button onclick={submit} disabled={saving || !name.trim()}>
      {saving ? "Creating…" : "Create home"}
    </Button>
  {/snippet}
</Modal>

<style>
  .form { display: flex; flex-direction: column; gap: 16px; }

  .type-group {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 4px 8px 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .type-group legend { font-size: 12px; color: var(--text-muted); padding: 0 4px; }

  .type-option {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px;
    border-radius: var(--radius);
    cursor: pointer;
    border: 1px solid transparent;
  }
  .type-option:hover { background: var(--surface-hover); }
  .type-option.selected { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, transparent); }
  .type-option input[type="radio"] { position: absolute; opacity: 0; }

  .type-icon { font-size: 20px; flex-shrink: 0; margin-top: 2px; }
  .type-body { display: flex; flex-direction: column; gap: 2px; }
  .type-body strong { font-size: 13px; font-weight: 600; color: var(--text); }
  .type-body small { font-size: 12px; color: var(--text-muted); }

  .error { color: var(--danger, #c0392b); font-size: 13px; margin: 0; }
</style>
