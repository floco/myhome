<script lang="ts">
  interface Props {
    value: string;
    onchange?: (v: string) => void;
  }
  let { value = $bindable(), onchange }: Props = $props();

  const EMOJIS = [
    // Home & Rooms
    "🏠","🏡","🛋","🛏","🚪","🪟","🪑","🛁","🚿","🪠","🔑","🪪",
    // Cleaning
    "🧹","🧺","🧻","🪣","🧴","🧼","🧽","🪥","🫧","🧷",
    // Tools & Maintenance
    "🔧","🔨","⚙️","🪛","🪚","🔩","🪜","🧰","🛠","🪤",
    // Electronics
    "🔌","💡","🔋","📱","💻","🖥","📺","🎮","📷","📸",
    // Kitchen
    "🍽","🫙","🍳","🥄","🔪","🫖","☕","🥤","🥛","🧃","🧊",
    // Health & Safety
    "💊","🩺","🩹","🧬","💉","🧪","🔐","🔒","🛡",
    // Plants & Nature
    "🌱","🪴","🌿","🍀","🌸","🌻","🪵","🌲",
    // Shopping & Money
    "📦","📋","🛒","💰","💶","💵","💳","🎁","🛍","🗑",
    // Status & Schedule
    "✅","⚠️","❌","⭐","📌","📅","⏰","🔔","🚨","🏷",
    // Transport
    "🚗","🚲","🛵","✈️","⛽",
    // Food & Consumables
    "🍞","🧈","🥚","🧀","🥫","🧂","🍫","🌶","🥜",
    // Personal care
    "🪷","💈","🎒","🧢","🧣","🧤",
    // Misc
    "🧲","🔦","💎","🎀","🎉","🏆","🎯","🧩","📚","🖊",
  ];

  let open = $state(false);
  let customValue = $state("");
  let wrapper = $state<HTMLElement | null>(null);
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let panelLeft = $state(0);
  let panelTop = $state(0);

  function openPicker(): void {
    if (!open && triggerEl) {
      const rect = triggerEl.getBoundingClientRect();
      panelLeft = Math.max(4, Math.min(rect.left, window.innerWidth - 248));
      panelTop = rect.bottom + 4;
    }
    open = !open;
    if (!open) customValue = "";
  }

  function select(e: string): void {
    value = e;
    onchange?.(e);
    open = false;
    customValue = "";
  }

  function applyCustom(): void {
    const v = customValue.trim();
    if (v) select(v);
  }

  function handleClickOutside(e: MouseEvent): void {
    if (!wrapper) return;
    if (!wrapper.contains(e.target as Node)) {
      open = false;
      customValue = "";
    }
  }

  function handleWindowKeydown(e: KeyboardEvent): void {
    if (open && e.key === "Escape") {
      open = false;
      customValue = "";
    }
  }
</script>

<svelte:window onclick={handleClickOutside} onkeydown={handleWindowKeydown} />

<span class="ep-wrap" bind:this={wrapper}>
  <button
    class="ep-trigger"
    bind:this={triggerEl}
    onclick={openPicker}
    type="button"
    title="Pick emoji"
  >
    <span class="ep-current">{value || "?"}</span>
    <span class="ep-caret">▾</span>
  </button>

  {#if open}
    <div class="ep-panel" style="left:{panelLeft}px;top:{panelTop}px">
      <div class="ep-grid">
        {#each EMOJIS as e (e)}
          <button
            class="ep-emoji"
            class:ep-selected={value === e}
            type="button"
            onclick={() => select(e)}
          >{e}</button>
        {/each}
      </div>
      <div class="ep-custom">
        <input
          class="ep-custom-input"
          bind:value={customValue}
          placeholder="Custom…"
          maxlength="4"
          onkeydown={(ev) => { if (ev.key === "Enter") { ev.preventDefault(); applyCustom(); } }}
        />
        <button
          class="ep-apply"
          type="button"
          onclick={applyCustom}
          disabled={!customValue.trim()}
        >✓</button>
      </div>
    </div>
  {/if}
</span>

<style>
  .ep-wrap { position: relative; display: inline-flex; }

  .ep-trigger {
    display: inline-flex; align-items: center; gap: 3px;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 3px 6px 3px 8px; cursor: pointer;
    font-size: 18px; line-height: 1;
  }
  .ep-trigger:hover { border-color: var(--accent); }
  .ep-caret { font-size: 9px; color: var(--text-faint); }
  .ep-current { min-width: 1.2em; text-align: center; }

  .ep-panel {
    position: fixed; z-index: 9999;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    padding: 8px; width: 240px;
  }

  .ep-grid {
    display: grid; grid-template-columns: repeat(9, 1fr);
    gap: 1px; max-height: 216px; overflow-y: auto;
    margin-bottom: 6px;
  }

  .ep-emoji {
    background: none; border: none; border-radius: 3px;
    cursor: pointer; font-size: 17px; padding: 3px 2px;
    line-height: 1; text-align: center;
  }
  .ep-emoji:hover { background: var(--surface-hover); }
  .ep-emoji.ep-selected {
    background: color-mix(in srgb, var(--accent) 20%, transparent);
    outline: 1px solid var(--accent);
  }

  .ep-custom { display: flex; gap: 4px; }
  .ep-custom-input {
    flex: 1; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); padding: 4px 8px;
    font-size: 14px; font-family: var(--font-sans);
  }
  .ep-custom-input::placeholder { color: var(--text-faint); }
  .ep-custom-input:focus { outline: none; border-color: var(--accent); }
  .ep-apply {
    background: var(--accent); border: none; border-radius: var(--radius-sm);
    color: var(--accent-contrast); padding: 4px 10px; cursor: pointer; font-size: 12px;
  }
  .ep-apply:disabled { opacity: 0.4; cursor: default; }
</style>
