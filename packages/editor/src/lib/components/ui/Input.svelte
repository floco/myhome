<!-- packages/editor/src/lib/components/ui/Input.svelte -->
<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";

  interface Props extends Omit<HTMLInputAttributes, "value" | "class"> {
    value?: string;
    /** Optional visible label; the input is wrapped in a <label> so clicking it focuses the field. */
    label?: string;
  }
  let { value = $bindable(""), placeholder = "", type = "text", label, ...rest }: Props = $props();
</script>

{#if label}
  <label class="ui-input-field">
    <span class="ui-input-label">{label}</span>
    <input class="ui-input" {type} {placeholder} bind:value {...rest} />
  </label>
{:else}
  <input class="ui-input" {type} {placeholder} bind:value {...rest} />
{/if}

<style>
  .ui-input {
    font-family: var(--font-sans);
    font-size: 13px;
    background: var(--surface-alt);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 8px 12px;
    width: 100%;
    height: 36px;
    box-sizing: border-box;
  }
  .ui-input:focus { outline: none; border-color: var(--accent); }
  .ui-input::placeholder { color: var(--text-faint); }
  .ui-input-field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
  .ui-input-label {
    font-size: 0.75rem; font-weight: 600; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.05em;
  }
</style>
