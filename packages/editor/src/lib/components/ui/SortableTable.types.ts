import type { Snippet } from "svelte";

export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  sortValue?: (row: T) => string | number | Date | null | undefined;
  cell?: Snippet<[T]>;
  headerClass?: string;
  cellClass?: string | ((row: T) => string);
  stopRowClick?: boolean;
}
