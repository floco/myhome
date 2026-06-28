<script lang="ts">
  import ChoreRow from "../../src/lib/components/ChoreRow.svelte";
  let { onParentClick }: { onParentClick: () => void } = $props();

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onParentClick();
    }
  }
</script>

<div role="button" tabindex="0" onclick={onParentClick} onkeydown={handleKeydown}>
  <ChoreRow emoji="🧹" name="Sweep" dueLabel="Today" dueColor="#4caf50" oncomplete={() => {}} />
</div>
