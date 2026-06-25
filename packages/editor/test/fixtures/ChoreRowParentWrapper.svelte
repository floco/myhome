<script lang="ts">
  import ChoreRow from "../../src/lib/components/ChoreRow.svelte";
  let { onParentClick }: { onParentClick: () => void } = $props();
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div onclick={onParentClick}>
  <ChoreRow emoji="🧹" name="Sweep" dueLabel="Today" dueColor="#4caf50" oncomplete={() => {}} />
</div>
