<script lang="ts">
  let { onclose }: { entry: any; costsStore: any; settingsStore: any; floorStore: any; onclose: () => void } = $props();
</script>
<div class="overlay" onclick={onclose} style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center">
  <div style="background:#1a1a30;padding:20px;border-radius:8px;color:#ccc;font-family:sans-serif">Entry modal — coming soon</div>
</div>
