<!-- packages/editor/src/lib/components/WorkModal.svelte -->
<!-- Stub — full implementation in Task 9 -->
<script lang="ts">
  import type { createWorksStore, Work } from "../worksStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";

  type WorksStore = ReturnType<typeof createWorksStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    work: Work | null;
    store: WorksStore;
    settingsStore: SettingsStore;
    onclose: () => void;
    onplaceonmap?: (workId: string) => void;
  }

  let { onclose }: Props = $props();
</script>

<div class="modal-backdrop" onclick={onclose}></div>

<style>
  .modal-backdrop {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 100;
  }
</style>
