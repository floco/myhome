<script lang="ts">
  import ChoreEditModal from "../../src/lib/components/ChoreEditModal.svelte";
  import type { Chore } from "../../src/lib/choreStore.svelte";

  interface Props {
    initialChore: Chore;
    updatedChore: Chore;
    store: unknown;
    rooms: Array<{ id: string; label: string; polygon: { x: number; y: number }[] | null }>;
  }
  let { initialChore, updatedChore, store, rooms }: Props = $props();

  let chore = $state(initialChore);

  export function applyUpdate(): void {
    chore = updatedChore;
  }
</script>

<ChoreEditModal {chore} store={store as never} {rooms} onclose={() => {}} />
