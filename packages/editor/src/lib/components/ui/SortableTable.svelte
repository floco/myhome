<!-- packages/editor/src/lib/components/ui/SortableTable.svelte -->
<script lang="ts" generics="T">
  import type { Snippet } from "svelte";
  import { createSortState, type SortState } from "../../utils/sortState.svelte";
  import type { Column } from "./SortableTable.types";

  interface Props {
    columns: Column<T>[];
    rows: T[];
    rowKey: (row: T) => string | number;
    rowClick?: (row: T) => void;
    rowClass?: (row: T) => string;
    defaultSort?: SortState;
    emptyMessage?: string;
    class?: string;
    extraRow?: Snippet;
    isRowExpanded?: (row: T) => boolean;
    expandedRow?: Snippet<[T]>;
  }

  let {
    columns,
    rows,
    rowKey,
    rowClick,
    rowClass,
    defaultSort,
    emptyMessage,
    class: className,
    extraRow,
    isRowExpanded,
    expandedRow,
  }: Props = $props();

  const sortState = createSortState(defaultSort ?? null);

  const sortedRows = $derived.by(() => {
    const current = sortState.current;
    if (!current) return rows;
    const col = columns.find((c) => c.key === current.key);
    if (!col?.sortValue) return rows;
    return sortState.sortRows(rows, col.sortValue);
  });

  function ariaSortFor(key: string): "ascending" | "descending" | "none" {
    const dir = sortState.directionFor(key);
    if (dir === "asc") return "ascending";
    if (dir === "desc") return "descending";
    return "none";
  }

  function arrowFor(key: string): string {
    const dir = sortState.directionFor(key);
    if (dir === "asc") return "▲";
    if (dir === "desc") return "▼";
    return "";
  }

  function cellClassFor(column: Column<T>, row: T): string | undefined {
    return typeof column.cellClass === "function" ? column.cellClass(row) : column.cellClass;
  }
</script>

<table class="ui-sortable-table {className ?? ''}">
  <thead>
    <tr>
      {#each columns as column (column.key)}
        {#if column.sortable === false}
          <th class={column.headerClass}>{column.label}</th>
        {:else}
          <th class={column.headerClass} aria-sort={ariaSortFor(column.key)}>
            <button type="button" class="ui-sortable-table-sort-btn" onclick={() => sortState.toggle(column.key)}>
              {column.label}
              <span class="ui-sortable-table-arrow">{arrowFor(column.key)}</span>
            </button>
          </th>
        {/if}
      {/each}
    </tr>
  </thead>
  <tbody>
    {#each sortedRows as row (rowKey(row))}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
      <tr onclick={rowClick ? () => rowClick(row) : undefined} class="{rowClass?.(row) ?? ''} {rowClick ? 'clickable' : ''}">
        {#each columns as column (column.key)}
          <td
            class={cellClassFor(column, row)}
            onclick={column.stopRowClick ? (e) => e.stopPropagation() : undefined}
          >
            {#if column.cell}
              {@render column.cell(row)}
            {:else}
              {column.sortValue?.(row) ?? "—"}
            {/if}
          </td>
        {/each}
      </tr>
      {#if expandedRow && isRowExpanded?.(row)}
        <tr class="ui-sortable-table-expand-row">
          <td colspan={columns.length}>{@render expandedRow(row)}</td>
        </tr>
      {/if}
    {/each}

    {#if extraRow}
      <tr>{@render extraRow()}</tr>
    {/if}

    {#if rows.length === 0 && emptyMessage}
      <tr>
        <td colspan={columns.length} class="ui-sortable-table-empty">{emptyMessage}</td>
      </tr>
    {/if}
  </tbody>
</table>

<style>
  .ui-sortable-table { width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-muted); }
  .ui-sortable-table thead { position: sticky; top: 0; background: var(--surface-alt); z-index: 1; }
  .ui-sortable-table th {
    padding: 6px 10px; color: var(--text-faint); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.05em;
    text-align: left; border-bottom: 1px solid var(--border);
  }
  .ui-sortable-table-sort-btn {
    display: inline-flex; align-items: center; gap: 4px;
    background: none; border: none; padding: 0; margin: 0;
    color: inherit; font: inherit; text-transform: inherit; letter-spacing: inherit;
    cursor: pointer;
  }
  .ui-sortable-table-sort-btn:hover { color: var(--text); }
  .ui-sortable-table-arrow { font-size: 8px; min-width: 8px; display: inline-block; }
  .ui-sortable-table td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  .ui-sortable-table tr:hover td { background: var(--surface-hover); }
  .ui-sortable-table tr.clickable:hover td { cursor: pointer; }
  .ui-sortable-table-expand-row td { background: var(--surface-alt); padding: 0; cursor: default; }
  .ui-sortable-table-empty { text-align: center; color: var(--text-faint); padding: 32px; }
</style>
