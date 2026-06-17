<script lang="ts">
  import type { Room } from "@myhome/geometry";

  let {
    room,
    haAreas = [],
    onupdate,
  }: {
    room: Room;
    haAreas?: Array<{ area_id: string; name: string }>;
    onupdate: (patch: { label?: string; haAreaId?: string | null }) => void;
  } = $props();

  let labelDraft = $state("");
  let areaDraft = $state("");

  $effect(() => {
    labelDraft = room.label;
    areaDraft = room.haAreaId ?? "";
  });

  function commitLabel(): void {
    const trimmed = labelDraft.trim();
    if (trimmed !== room.label) onupdate({ label: trimmed });
  }

  function commitArea(): void {
    const trimmed = areaDraft.trim();
    const next = trimmed === "" ? null : trimmed;
    if (next !== room.haAreaId) onupdate({ haAreaId: next });
  }
</script>

<aside class="room-panel">
  <h2>Room</h2>

  <label>
    <span>Label</span>
    <input
      type="text"
      bind:value={labelDraft}
      onblur={commitLabel}
      onkeydown={(e) => {
        if (e.key === "Enter") {
          commitLabel();
          (e.target as HTMLInputElement).blur();
        }
      }}
    />
  </label>

  <label>
    <span>HA Area ID</span>
    <input
      type="text"
      placeholder="(none)"
      bind:value={areaDraft}
      onblur={commitArea}
      onkeydown={(e) => {
        if (e.key === "Enter") {
          commitArea();
          (e.target as HTMLInputElement).blur();
        }
      }}
    />
  </label>

  <p class="area-display">{room.areaM2} m²</p>
</aside>

<style>
  .room-panel {
    width: 200px;
    background: #2a2a2a;
    border-left: 1px solid #444;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex-shrink: 0;
    overflow-y: auto;
  }
  h2 {
    margin: 0;
    font-size: 13px;
    color: #ccc;
    font-weight: 600;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  span {
    font-size: 11px;
    color: #888;
  }
  input {
    background: #1c1c1c;
    border: 1px solid #555;
    border-radius: 3px;
    color: #eee;
    padding: 4px 6px;
    font-size: 12px;
    font-family: inherit;
  }
  input:focus {
    outline: none;
    border-color: #5af;
  }
  .area-display {
    margin: 0;
    font-size: 12px;
    color: #888;
  }
</style>
