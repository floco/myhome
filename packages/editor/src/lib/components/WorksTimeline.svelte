<script lang="ts">
  import type { Work } from "../worksStore.svelte";

  interface Props {
    works: Work[];
    onworkclick?: (id: string) => void;
  }
  let { works, onworkclick }: Props = $props();

  const VIEW_W = 1000;
  const VIEW_H = 140;
  const PAD_X = 30;
  const MARGIN_TOP = 10;
  const MARGIN_BOTTOM = 24;
  const CENTER_Y = MARGIN_TOP + (VIEW_H - MARGIN_TOP - MARGIN_BOTTOM) / 2;
  const LANE_HEIGHT = 10;
  const MAX_LANE = 5;
  const MIN_GAP = 16;
  const DOT_R = 4;

  const STATUS_COLOR: Record<Work["status"], string> = {
    done: "#33aa66",
    in_progress: "#3388cc",
    planned: "#cc8833",
  };
  const STATUS_LABEL: Record<Work["status"], string> = {
    done: "Done",
    in_progress: "In progress",
    planned: "Planned",
  };

  const timeRange = $derived((() => {
    if (works.length === 0) {
      const now = Date.now();
      return { min: now, max: now };
    }
    const times = works.map((w) => new Date(w.date).getTime());
    return { min: Math.min(...times), max: Math.max(...times) };
  })());

  function xForTime(t: number): number {
    const { min, max } = timeRange;
    if (max === min) return VIEW_W / 2;
    return PAD_X + ((t - min) / (max - min)) * (VIEW_W - 2 * PAD_X);
  }

  interface Dot {
    work: Work;
    x: number;
    y: number;
  }

  // Works whose dates land close together on the x-axis get assigned to
  // alternating vertical "lanes" (0, +1, -1, +2, -2, ...) so their dots
  // never overlap -- processed left-to-right, tracking each lane's last
  // placed x so a lane is only reused once it's far enough away again.
  const dots = $derived((() => {
    const sorted = [...works]
      .map((w) => ({ work: w, x: xForTime(new Date(w.date).getTime()) }))
      .sort((a, b) => a.x - b.x);

    const laneLastX = new Map<number, number>();
    const result: Dot[] = [];
    for (const item of sorted) {
      let lane = 0;
      let assigned = false;
      for (let offset = 0; offset <= MAX_LANE && !assigned; offset++) {
        const candidates = offset === 0 ? [0] : [offset, -offset];
        for (const cand of candidates) {
          const last = laneLastX.get(cand);
          if (last === undefined || item.x - last >= MIN_GAP) {
            lane = cand;
            assigned = true;
            break;
          }
        }
      }
      laneLastX.set(lane, item.x);
      result.push({ work: item.work, x: item.x, y: CENTER_Y + lane * LANE_HEIGHT });
    }
    return result;
  })());

  const yearTicks = $derived((() => {
    const startYear = new Date(timeRange.min).getFullYear();
    const endYear = new Date(timeRange.max).getFullYear();
    const ticks: { year: number; x: number }[] = [];
    for (let y = startYear; y <= endYear; y++) {
      const jan1 = new Date(Date.UTC(y, 0, 1)).getTime();
      const x = Math.min(Math.max(xForTime(jan1), PAD_X), VIEW_W - PAD_X);
      ticks.push({ year: y, x });
    }
    if (ticks.length === 0) {
      ticks.push({ year: startYear, x: VIEW_W / 2 });
    }
    return ticks;
  })());

  const todayX = $derived((() => {
    const now = Date.now();
    if (now < timeRange.min || now > timeRange.max) return null;
    return xForTime(now);
  })());

  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }
</script>

<div class="timeline-wrap">
  <svg viewBox="0 0 {VIEW_W} {VIEW_H}" preserveAspectRatio="none" style="width:100%; height:{VIEW_H}px;">
    <line x1={PAD_X} y1={CENTER_Y} x2={VIEW_W - PAD_X} y2={CENTER_Y} stroke="var(--border)" stroke-width="1" />

    {#each yearTicks as t (t.year)}
      <line x1={t.x} y1={MARGIN_TOP} x2={t.x} y2={VIEW_H - MARGIN_BOTTOM + 4} stroke="var(--border)" stroke-width="1" stroke-dasharray="2 2" />
      <text x={t.x} y={VIEW_H - 8} text-anchor="middle" font-size="10" fill="var(--text-faint)" font-family="sans-serif">{t.year}</text>
    {/each}

    {#if todayX !== null}
      <line x1={todayX} y1={MARGIN_TOP} x2={todayX} y2={VIEW_H - MARGIN_BOTTOM} stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="3 3" />
    {/if}

    {#each dots as d (d.work.id)}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <circle
        cx={d.x}
        cy={d.y}
        r={DOT_R}
        fill={STATUS_COLOR[d.work.status]}
        opacity="0.9"
        style="cursor:{onworkclick ? 'pointer' : 'default'}"
        onclick={() => onworkclick?.(d.work.id)}
      >
        <title>{d.work.title} — {STATUS_LABEL[d.work.status]} — {formatDate(d.work.date)}{d.work.totalCost != null ? ` — ${d.work.totalCost.toLocaleString(undefined, { maximumFractionDigits: 0 })} €` : ""}</title>
      </circle>
    {/each}
  </svg>

  <div class="legend">
    <span class="legend-item"><span class="dot" style="background:{STATUS_COLOR.done}"></span>Done</span>
    <span class="legend-item"><span class="dot" style="background:{STATUS_COLOR.in_progress}"></span>In progress</span>
    <span class="legend-item"><span class="dot" style="background:{STATUS_COLOR.planned}"></span>Planned</span>
  </div>
</div>

<style>
  .timeline-wrap { width: 100%; }
  .legend { display: flex; gap: 16px; margin-top: 4px; padding-left: 4px; }
  .legend-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-muted); }
  .legend .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
</style>
