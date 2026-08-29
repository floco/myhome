export type Alignment = "left" | "center" | "right";

export interface ParsedTable {
  startIndex: number;
  endIndex: number;
  headerCells: string[];
  alignments: Alignment[];
  rows: string[][];
}

function escapeCell(s: string): string {
  return s.replace(/\|/g, "\\|").replace(/\n/g, " ");
}

function splitRow(line: string): string[] {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  const cells: string[] = [];
  let cur = "";
  for (let i = 0; i < s.length; i++) {
    if (s[i] === "\\" && s[i + 1] === "|") {
      cur += "|";
      i++;
      continue;
    }
    if (s[i] === "|") {
      cells.push(cur.trim());
      cur = "";
      continue;
    }
    cur += s[i];
  }
  cells.push(cur.trim());
  return cells;
}

function isTableRowLine(line: string): boolean {
  return line.includes("|") && line.trim().length > 0;
}

function isSeparatorRow(line: string): boolean {
  const cells = splitRow(line);
  return cells.length > 0 && cells.every((c) => /^:?-+:?$/.test(c.trim()));
}

function alignmentFromSeparatorCell(cell: string): Alignment {
  const c = cell.trim();
  if (c.startsWith(":") && c.endsWith(":")) return "center";
  if (c.endsWith(":")) return "right";
  return "left";
}

/** Finds the GFM pipe-table block (if any) that the cursor sits inside. */
export function findTableAtCursor(value: string, cursorPos: number): ParsedTable | null {
  const lines = value.split("\n");
  const offsets: number[] = [];
  let acc = 0;
  for (const l of lines) {
    offsets.push(acc);
    acc += l.length + 1;
  }

  let cursorLine = lines.length - 1;
  for (let i = 0; i < lines.length; i++) {
    if (cursorPos <= offsets[i] + lines[i].length) {
      cursorLine = i;
      break;
    }
  }

  if (!isTableRowLine(lines[cursorLine])) return null;

  let start = cursorLine;
  while (start > 0 && isTableRowLine(lines[start - 1])) start--;
  let end = cursorLine;
  while (end < lines.length - 1 && isTableRowLine(lines[end + 1])) end++;

  if (end - start < 1 || !isSeparatorRow(lines[start + 1])) return null;

  const headerCells = splitRow(lines[start]);
  const alignments = splitRow(lines[start + 1]).map(alignmentFromSeparatorCell);
  const rows: string[][] = [];
  for (let i = start + 2; i <= end; i++) rows.push(splitRow(lines[i]));

  return {
    startIndex: offsets[start],
    endIndex: offsets[end] + lines[end].length,
    headerCells,
    alignments,
    rows,
  };
}

/** Builds a GFM pipe-table markdown block from a grid of cells. */
export function serializeTable(headerCells: string[], alignments: Alignment[], rows: string[][]): string {
  const cellLine = (cells: string[]) => "| " + cells.map(escapeCell).join(" | ") + " |";
  const sepCell = (a: Alignment) => (a === "center" ? ":---:" : a === "right" ? "---:" : ":---");
  const lines = [cellLine(headerCells), "| " + alignments.map(sepCell).join(" | ") + " |", ...rows.map(cellLine)];
  return lines.join("\n");
}
