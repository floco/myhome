<script lang="ts">
  export interface DonutSegment {
    id: string;
    label: string;
    emoji: string;
    color: string;
    valueLabel: string;
    pct: number;
  }

  interface Slice {
    seg: DonutSegment;
    startDeg: number;
    endDeg: number;
    midDeg: number;
  }

  interface Props {
    segments: DonutSegment[];
    centerLabel: string;
    centerValue: string;
    showLabels?: boolean;
    onsliceclick?: (id: string) => void;
  }
  let { segments, centerLabel, centerValue, showLabels = false, onsliceclick }: Props = $props();

  const CX = 155;
  const CY = 110;
  const OUTER_R = 70;
  const INNER_R = 28;

  function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) };
  }

  function donutPath(cx: number, cy: number, outerR: number, innerR: number, startDeg: number, endDeg: number): string {
    const clampedEnd = Math.min(startDeg + 359.99, endDeg);
    const os = polarPoint(cx, cy, outerR, startDeg);
    const oe = polarPoint(cx, cy, outerR, clampedEnd);
    const is = polarPoint(cx, cy, innerR, startDeg);
    const ie = polarPoint(cx, cy, innerR, clampedEnd);
    const large = clampedEnd - startDeg > 180 ? 1 : 0;
    return [
      `M ${os.x.toFixed(2)} ${os.y.toFixed(2)}`,
      `A ${outerR} ${outerR} 0 ${large} 1 ${oe.x.toFixed(2)} ${oe.y.toFixed(2)}`,
      `L ${ie.x.toFixed(2)} ${ie.y.toFixed(2)}`,
      `A ${innerR} ${innerR} 0 ${large} 0 ${is.x.toFixed(2)} ${is.y.toFixed(2)}`,
      "Z",
    ].join(" ");
  }

  const slices = $derived((() => {
    let angle = 0;
    return segments.map((seg) => {
      const start = angle;
      const span = (seg.pct / 100) * 360;
      angle += span;
      return { seg, startDeg: start, endDeg: angle, midDeg: start + span / 2 } as Slice;
    });
  })());
</script>

<svg viewBox="0 0 310 220" width="310" height="220" style="overflow:visible">
  {#each slices as s (s.seg.id)}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <path
      d={donutPath(CX, CY, OUTER_R, INNER_R, s.startDeg, s.endDeg)}
      fill={s.seg.color}
      opacity="0.9"
      style="cursor:{onsliceclick ? 'pointer' : 'default'}"
      onclick={() => onsliceclick?.(s.seg.id)}
    />
  {/each}

  <circle cx={CX} cy={CY} r={INNER_R} fill="var(--surface)" />
  <text x={CX} y={CY - 6} text-anchor="middle" fill="var(--text-muted)" font-size="8" font-family="sans-serif">{centerLabel}</text>
  <text x={CX} y={CY + 8} text-anchor="middle" fill="var(--text)" font-size="11" font-family="sans-serif" font-weight="600">{centerValue}</text>

  {#if showLabels}
    {#each slices as s (s.seg.id + "-label")}
      {@const mid = polarPoint(CX, CY, OUTER_R + 4, s.midDeg)}
      {@const elbow = polarPoint(CX, CY, OUTER_R + 18, s.midDeg)}
      {@const isRight = elbow.x >= CX}
      {@const lineEnd = { x: elbow.x + (isRight ? 28 : -28), y: elbow.y }}
      {@const textX = lineEnd.x + (isRight ? 4 : -4)}
      <line x1={mid.x} y1={mid.y} x2={elbow.x} y2={elbow.y} stroke={s.seg.color} stroke-width="1" opacity="0.7" />
      <line x1={elbow.x} y1={elbow.y} x2={lineEnd.x} y2={lineEnd.y} stroke={s.seg.color} stroke-width="1" opacity="0.7" />
      <circle cx={mid.x} cy={mid.y} r="2" fill={s.seg.color} />
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <text
        x={textX}
        y={elbow.y - 3}
        text-anchor={isRight ? "start" : "end"}
        fill={s.seg.color}
        font-size="9"
        font-family="sans-serif"
        font-weight="600"
        style="cursor:{onsliceclick ? 'pointer' : 'default'}"
        onclick={() => onsliceclick?.(s.seg.id)}
      >{s.seg.emoji} {s.seg.label}</text>
      <text
        x={textX}
        y={elbow.y + 9}
        text-anchor={isRight ? "start" : "end"}
        fill="var(--text-faint)"
        font-size="8"
        font-family="sans-serif"
      >{s.seg.valueLabel} · {s.seg.pct.toFixed(0)}%</text>
    {/each}
  {/if}
</svg>
