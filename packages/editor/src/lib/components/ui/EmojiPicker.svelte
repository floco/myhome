<script lang="ts">
  import { _ } from "svelte-i18n";
  import { COUNTRY_FLAGS } from "../../countryFlags";
  import Tabs from "./Tabs.svelte";

  interface Props {
    value: string;
    onchange?: (v: string) => void;
    flags?: boolean;
  }
  let { value = $bindable(), onchange, flags = false }: Props = $props();

  let activeTab = $state<"objects" | "flags">("objects");
  let flagFilter = $state("");
  let objectFilter = $state("");

  const filteredFlags = $derived(
    flagFilter.trim()
      ? COUNTRY_FLAGS.filter((c) => c.name.toLowerCase().includes(flagFilter.trim().toLowerCase()))
      : COUNTRY_FLAGS,
  );

  // Keywords per emoji so the search box can filter the grid -- the emoji
  // itself carries no searchable text.
  const EMOJI_NAMES: Record<string, string> = {
    "🏠": "house home", "🏡": "house garden home", "🛋": "sofa couch",
    "🛏": "bed", "🚪": "door", "🪟": "window", "🪑": "chair",
    "🛁": "bathtub bath", "🚿": "shower", "🪠": "plunger", "🔑": "key",
    "🪪": "id card license",
    "🧹": "broom clean sweep", "🧺": "basket laundry",
    "🧻": "toilet paper roll", "🪣": "bucket", "🧴": "lotion bottle",
    "🧼": "soap clean", "🧽": "sponge clean", "🪥": "toothbrush",
    "🫧": "bubbles clean", "🧷": "safety pin",
    "🔧": "wrench tool", "🔨": "hammer tool", "⚙️": "gear settings",
    "🪛": "screwdriver tool", "🪚": "saw tool", "🔩": "bolt nut",
    "🪜": "ladder", "🧰": "toolbox", "🛠": "hammer wrench tools",
    "🪤": "mouse trap",
    "🔌": "plug electric", "💡": "bulb light idea", "🔋": "battery",
    "📱": "phone mobile", "💻": "laptop computer", "🖥": "desktop monitor computer",
    "📺": "tv television", "🎮": "game controller", "📷": "camera photo",
    "📸": "camera flash photo",
    "🍽": "plate dinner food", "🫙": "jar", "🍳": "pan cooking egg fry",
    "🥄": "spoon", "🔪": "knife", "🫖": "teapot tea",
    "☕": "coffee cup", "🥤": "drink cup soda", "🥛": "milk glass",
    "🧃": "juice box drink", "🧊": "ice",
    "💊": "pill medicine", "🩺": "stethoscope doctor health",
    "🩹": "bandage", "🧬": "dna", "💉": "syringe injection",
    "🧪": "test tube science", "🔐": "locked security", "🔒": "lock",
    "🛡": "shield security",
    "🌱": "seedling plant", "🪴": "potted plant", "🌿": "herb leaf plant",
    "🍀": "clover luck", "🌸": "flower blossom", "🌻": "sunflower",
    "🪵": "wood log", "🌲": "tree",
    "📦": "box package", "📋": "clipboard list", "🛒": "cart shopping",
    "💰": "money bag", "💶": "euro money", "💵": "dollar money",
    "💳": "credit card", "🎁": "gift", "🛍": "shopping bags",
    "🗑": "trash bin garbage",
    "✅": "check done", "⚠️": "warning", "❌": "cross error",
    "⭐": "star", "📌": "pin", "📅": "calendar date",
    "⏰": "alarm clock", "🔔": "bell notification", "🚨": "alert siren",
    "🏷": "tag label",
    "🚗": "car", "🚲": "bike bicycle", "🛵": "scooter moped",
    "✈️": "plane airplane", "⛽": "fuel gas",
    "🍞": "bread", "🧈": "butter", "🥚": "egg", "🧀": "cheese",
    "🥫": "can food", "🧂": "salt", "🍫": "chocolate", "🌶": "pepper spice",
    "🥜": "peanut nuts",
    "🪷": "lotus flower", "💈": "barber", "🎒": "backpack bag",
    "🧢": "cap hat", "🧣": "scarf", "🧤": "gloves",
    "🧲": "magnet", "🔦": "flashlight torch", "💎": "gem diamond",
    "🎀": "ribbon bow", "🎉": "party celebration", "🏆": "trophy",
    "🎯": "target dart", "🧩": "puzzle", "📚": "books", "🖊": "pen",
  };

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

  const filteredEmojis = $derived(
    objectFilter.trim()
      ? EMOJIS.filter((e) => (EMOJI_NAMES[e] ?? "").includes(objectFilter.trim().toLowerCase()))
      : EMOJIS,
  );

  let open = $state(false);
  let customValue = $state("");
  let wrapper = $state<HTMLElement | null>(null);
  let panelEl = $state<HTMLElement | null>(null);
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let panelLeft = $state(0);
  let panelTop = $state(0);

  // Teleport the panel to <body> so position:fixed isn't affected by
  // ancestor CSS transforms (e.g. Modal uses translate(-50%,-50%)).
  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  const PANEL_WIDTH = 340;

  function openPicker(): void {
    if (!open && triggerEl) {
      const rect = triggerEl.getBoundingClientRect();
      panelLeft = Math.max(4, Math.min(rect.left, window.innerWidth - PANEL_WIDTH - 8));
      panelTop = rect.bottom + 4;
    }
    open = !open;
    if (!open) {
      customValue = "";
    } else {
      activeTab = "objects";
      flagFilter = "";
      objectFilter = "";
    }
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
    const target = e.target as Node;
    // Panel is portal'd to body so check both trigger wrapper and panel
    if (wrapper?.contains(target) || panelEl?.contains(target)) return;
    open = false;
    customValue = "";
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
    title={$_('emojiPicker.pickEmoji')}
  >
    <span class="ep-current">{value || "?"}</span>
    <span class="ep-caret">▾</span>
  </button>

  {#if open}
    <div class="ep-panel" style="left:{panelLeft}px;top:{panelTop}px" bind:this={panelEl} use:portal>
      {#if flags}
        <Tabs
          tabs={[{ id: "objects", label: $_('emojiPicker.objects') }, { id: "flags", label: $_('emojiPicker.flags') }]}
          active={activeTab}
          onchange={(id) => { activeTab = id as "objects" | "flags"; }}
        />
      {/if}
      {#if !flags || activeTab === "objects"}
        <input
          class="ep-filter"
          bind:value={objectFilter}
          placeholder={$_('emojiPicker.filterEmojis')}
        />
        <div class="ep-grid">
          {#each filteredEmojis as e (e)}
            <button
              class="ep-emoji"
              class:ep-selected={value === e}
              type="button"
              title={EMOJI_NAMES[e]}
              onclick={() => select(e)}
            >{e}</button>
          {/each}
        </div>
      {:else}
        <input
          class="ep-filter"
          bind:value={flagFilter}
          placeholder={$_('emojiPicker.filterCountries')}
        />
        <div class="ep-grid ep-flag-grid">
          {#each filteredFlags as c (c.code)}
            <button
              class="ep-emoji"
              class:ep-selected={value === c.flag}
              type="button"
              title={c.name}
              onclick={() => select(c.flag)}
            >{c.flag}</button>
          {/each}
        </div>
      {/if}
      <div class="ep-custom">
        <input
          class="ep-custom-input"
          bind:value={customValue}
          placeholder={$_('emojiPicker.custom')}
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
    display: inline-flex; align-items: center; justify-content: center; gap: 3px;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 0 8px; cursor: pointer;
    font-size: 18px; line-height: 1;
    height: 36px; box-sizing: border-box;
  }
  .ep-trigger:hover { border-color: var(--accent); }
  .ep-caret { font-size: 9px; color: var(--text-faint); }
  .ep-current { min-width: 1.2em; text-align: center; }

  .ep-panel {
    position: fixed; z-index: 9999;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    padding: 10px; width: 340px;
  }

  .ep-grid {
    display: grid; grid-template-columns: repeat(6, 1fr);
    gap: 2px; max-height: 400px; overflow-y: auto; overflow-x: hidden;
    margin-bottom: 6px;
  }

  .ep-emoji {
    background: none; border: none; border-radius: 4px;
    cursor: pointer; font-size: 34px; padding: 6px 4px;
    line-height: 1; text-align: center;
  }
  .ep-emoji:hover { background: var(--surface-hover); }
  .ep-emoji.ep-selected {
    background: color-mix(in srgb, var(--accent) 20%, transparent);
    outline: 1px solid var(--accent);
  }

  .ep-filter {
    width: 100%; box-sizing: border-box; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); padding: 6px 8px; font-size: 13px;
    font-family: var(--font-sans); margin-bottom: 6px;
  }
  .ep-filter:focus { outline: none; border-color: var(--accent); }

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
