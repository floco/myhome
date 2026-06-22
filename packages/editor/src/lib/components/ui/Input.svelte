<!-- packages/editor/src/lib/components/ui/Input.svelte -->
<script lang="ts">
  interface Props {
    value?: string;
    placeholder?: string;
    type?: string;
  }
  let { value = $bindable(""), placeholder = "", type = "text" }: Props = $props();
</script>

<input class="ui-input" {type} {placeholder} bind:value />

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
    box-sizing: border-box;
  }
  .ui-input:focus { outline: none; border-color: var(--accent); }
  .ui-input::placeholder { color: var(--text-faint); }
</style>
