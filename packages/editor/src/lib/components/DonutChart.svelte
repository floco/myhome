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
    compact?: boolean;
    onsliceclick?: (id: string) => void;
  }
  let {
    segments,
    centerLabel,
    centerValue,
    showLabels = false,
    compact = false,
    onsliceclick,
  }: Props = $props();

  // The connector-line labels need extra side margin to fit within the
  // chart's own box -- otherwise long labels (e.g. "Mortgage / Rent") bleed
  // into whatever sits next to the chart. Only widen when labels are shown;
  // the plain donut (dashboard widgets) keeps its original compact size.
  // `compact` scales the whole thing down further for the narrow dashboard
  // sidebar, which doesn't have the ~420px of width the full-page module
  // cards can spare for leader-line labels.
  const VIEW_W = compact ? (showLabels ? 340 : 220) : showLabels ? 420 : 310;
  const CX = VIEW_W / 2;
  const CY = compact ? 90 : 110;
  const VIEW_H = compact ? 180 : 220;
  const OUTER_R = compact ? 52 : 70;
  const INNER_R = compact ? 22 : 28;
  const LABEL_FONT = compact ? 8 : 9;
  const VALUE_FONT = compact ? 7 : 8;

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

  interface LabelPos {
    seg: DonutSegment;
    mid: { x: number; y: number };
    collarX: number;
    labelY: number;
    textX: number;
    isRight: boolean;
  }

  const LABEL_MIN_GAP = compact ? 14 : 20;
  const COLLAR_DIST = OUTER_R + (compact ? 14 : 22);
  const STUB_LEN = compact ? 7 : 10;

  // Spread a column of labels apart so none collide, keeping them as close
  // as possible to their desired (angle-derived) position and preserving
  // order -- a forward pass pushes later labels down, a backward pass pulls
  // earlier labels back up, splitting the spread evenly rather than
  // cascading everything toward one end.
  function declutter(desiredY: number[], minGap: number): number[] {
    const y = [...desiredY];
    for (let i = 1; i < y.length; i++) {
      y[i] = Math.max(y[i], y[i - 1] + minGap);
    }
    for (let i = y.length - 2; i >= 0; i--) {
      y[i] = Math.min(y[i], y[i + 1] - minGap);
    }
    return y;
  }

  // Slices whose angles cluster together would otherwise produce
  // overlapping leader-line labels. Each label connects with a single line
  // straight from its slice to a vertical "collar" per side (left/right of
  // center), where rows are decluttered top-to-bottom -- this uses the full
  // height around the donut and never lets connector lines cross.
  const labelPositions = $derived((() => {
    const raw = slices.map((s) => {
      const mid = polarPoint(CX, CY, OUTER_R + 4, s.midDeg);
      const desiredY = polarPoint(CX, CY, OUTER_R + 18, s.midDeg).y;
      const isRight = s.midDeg <= 180;
      return { seg: s.seg, mid, desiredY, isRight };
    });

    const result: LabelPos[] = [];
    for (const isRight of [true, false]) {
      const side = raw.filter((r) => r.isRight === isRight).sort((a, b) => a.desiredY - b.desiredY);
      const labelYs = declutter(side.map((r) => r.desiredY), LABEL_MIN_GAP);
      const collarX = CX + (isRight ? COLLAR_DIST : -COLLAR_DIST);
      side.forEach((r, i) => {
        result.push({
          seg: r.seg,
          mid: r.mid,
          collarX,
          labelY: labelYs[i],
          textX: collarX + (isRight ? STUB_LEN + 4 : -STUB_LEN - 4),
          isRight,
        });
      });
    }
    return result;
  })());
</script>

<svg viewBox="0 0 {VIEW_W} {VIEW_H}" width={VIEW_W} height={VIEW_H} style="overflow:visible">
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
    {#each labelPositions as l (l.seg.id + "-label")}
      <line x1={l.mid.x} y1={l.mid.y} x2={l.collarX} y2={l.labelY} stroke={l.seg.color} stroke-width="1" opacity="0.7" />
      <line
        x1={l.collarX}
        y1={l.labelY}
        x2={l.collarX + (l.isRight ? STUB_LEN : -STUB_LEN)}
        y2={l.labelY}
        stroke={l.seg.color}
        stroke-width="1"
        opacity="0.7"
      />
      <circle cx={l.mid.x} cy={l.mid.y} r="2" fill={l.seg.color} />
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <text
        x={l.textX}
        y={l.labelY - 3}
        text-anchor={l.isRight ? "start" : "end"}
        fill={l.seg.color}
        font-size={LABEL_FONT}
        font-family="sans-serif"
        font-weight="600"
        style="cursor:{onsliceclick ? 'pointer' : 'default'}"
        onclick={() => onsliceclick?.(l.seg.id)}
      >{l.seg.emoji} {l.seg.label}</text>
      <text
        x={l.textX}
        y={l.labelY + 9}
        text-anchor={l.isRight ? "start" : "end"}
        fill="var(--text-faint)"
        font-size={VALUE_FONT}
        font-family="sans-serif"
      >{l.seg.valueLabel} · {l.seg.pct.toFixed(0)}%</text>
    {/each}
  {/if}
</svg>
