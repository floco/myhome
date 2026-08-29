<!-- packages/editor/src/lib/components/ui/AttachmentIcon.svelte -->
<script lang="ts">
  interface Props {
    title?: string;
  }
  let { title }: Props = $props();
</script>

<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden={title ? undefined : "true"} role={title ? "img" : undefined}>
  {#if title}<title>{title}</title>{/if}
  <path
    d="M10.5 4.5v6a2.5 2.5 0 0 1-5 0v-7a1.5 1.5 0 0 1 3 0v6.5a0.5 0.5 0 0 1-1 0v-6"
    fill="none" stroke="currentColor" stroke-width="1.3"
    stroke-linecap="round" stroke-linejoin="round"
  />
</svg>
