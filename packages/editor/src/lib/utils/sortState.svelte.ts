export type SortDirection = "asc" | "desc";

export interface SortState {
  key: string;
  direction: SortDirection;
}

export function compareValues(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (a instanceof Date && b instanceof Date) return a.getTime() - b.getTime();
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { sensitivity: "base" });
}

export function createSortState(initial: SortState | null = null) {
  let state = $state<SortState | null>(initial);

  function toggle(key: string): void {
    if (!state || state.key !== key) {
      state = { key, direction: "asc" };
    } else if (state.direction === "asc") {
      state = { key, direction: "desc" };
    } else {
      state = null;
    }
  }

  function directionFor(key: string): SortDirection | null {
    return state && state.key === key ? state.direction : null;
  }

  function sortRows<T>(rows: T[], sortValue: (row: T) => unknown): T[] {
    if (!state) return rows;
    const dir = state.direction === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = sortValue(a);
      const vb = sortValue(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      return dir * compareValues(va, vb);
    });
  }

  return {
    get current() {
      return state;
    },
    toggle,
    directionFor,
    sortRows,
  };
}
