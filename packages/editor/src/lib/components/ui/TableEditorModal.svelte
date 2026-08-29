<!-- packages/editor/src/lib/components/ui/TableEditorModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Modal from "./Modal.svelte";
  import Button from "./Button.svelte";
  import type { Alignment, ParsedTable } from "./markdownTable";

  interface Props {
    initial: ParsedTable | null;
    onCancel: () => void;
    onConfirm: (headerCells: string[], alignments: Alignment[], rows: string[][]) => void;
  }
  let { initial, onCancel, onConfirm }: Props = $props();

  const isEditing = initial !== null;

  let headerCells = $state<string[]>(initial?.headerCells ?? ["", "", ""]);
  let alignments = $state<Alignment[]>(initial?.alignments ?? ["left", "left", "left"]);
  let rows = $state<string[][]>(initial?.rows ?? [["", "", ""], ["", "", ""]]);
  let selectedRow = $state<number | null>(null);
  let selectedColumn = $state<number | null>(null);

  function addRow(): void {
    rows = [...rows, headerCells.map(() => "")];
  }

  function removeRow(index: number): void {
    rows = rows.filter((_, i) => i !== index);
    if (selectedRow === index) selectedRow = null;
    else if (selectedRow !== null && selectedRow > index) selectedRow -= 1;
  }

  function addColumn(): void {
    headerCells = [...headerCells, ""];
    alignments = [...alignments, "left"];
    rows = rows.map((row) => [...row, ""]);
  }

  function removeColumn(index: number): void {
    if (headerCells.length <= 1) return;
    headerCells = headerCells.filter((_, i) => i !== index);
    alignments = alignments.filter((_, i) => i !== index);
    rows = rows.map((row) => row.filter((_, i) => i !== index));
    if (selectedColumn === index) selectedColumn = null;
    else if (selectedColumn !== null && selectedColumn > index) selectedColumn -= 1;
  }

  function setAlignment(index: number, alignment: Alignment): void {
    alignments = alignments.map((a, i) => (i === index ? alignment : a));
  }

  function toggleRowSelect(index: number): void {
    selectedRow = selectedRow === index ? null : index;
  }

  function toggleColumnSelect(index: number): void {
    selectedColumn = selectedColumn === index ? null : index;
  }

  function swap<T>(arr: T[], i: number, j: number): T[] {
    const next = [...arr];
    [next[i], next[j]] = [next[j], next[i]];
    return next;
  }

  function moveRow(index: number, delta: number): void {
    const target = index + delta;
    if (target < 0 || target >= rows.length) return;
    rows = swap(rows, index, target);
    if (selectedRow === index) selectedRow = target;
    else if (selectedRow === target) selectedRow = index;
  }

  function moveColumn(index: number, delta: number): void {
    const target = index + delta;
    if (target < 0 || target >= headerCells.length) return;
    headerCells = swap(headerCells, index, target);
    alignments = swap(alignments, index, target);
    rows = rows.map((row) => swap(row, index, target));
    if (selectedColumn === index) selectedColumn = target;
    else if (selectedColumn === target) selectedColumn = index;
  }

  function insertRowAbove(): void {
    if (selectedRow === null) return;
    const at = selectedRow;
    rows = [...rows.slice(0, at), headerCells.map(() => ""), ...rows.slice(at)];
    selectedRow = at + 1;
  }

  function insertRowBelow(): void {
    if (selectedRow === null) return;
    const at = selectedRow + 1;
    rows = [...rows.slice(0, at), headerCells.map(() => ""), ...rows.slice(at)];
  }

  function insertColumn(at: number): void {
    headerCells = [...headerCells.slice(0, at), "", ...headerCells.slice(at)];
    alignments = [...alignments.slice(0, at), "left", ...alignments.slice(at)];
    rows = rows.map((row) => [...row.slice(0, at), "", ...row.slice(at)]);
  }

  function insertColumnLeft(): void {
    if (selectedColumn === null) return;
    const at = selectedColumn;
    insertColumn(at);
    selectedColumn = at + 1;
  }

  function insertColumnRight(): void {
    if (selectedColumn === null) return;
    insertColumn(selectedColumn + 1);
  }

  function handleConfirm(): void {
    onConfirm(
      headerCells.map((c) => c.trim()),
      alignments,
      rows.map((row) => row.map((c) => c.trim())),
    );
  }
</script>

<Modal open={true} title={isEditing ? $_('markdownEditor.editTable') : $_('markdownEditor.insertTable')} onclose={onCancel} width="min(640px, 92vw)">
  <div class="te-grid-scroll">
    <table class="te-table">
      <thead>
        <tr class="te-header-row">
          {#each headerCells as _cell, i (i)}
            <th><input class="te-cell te-header-input" bind:value={headerCells[i]} /></th>
          {/each}
          <th class="te-actions-col"></th>
        </tr>
        <tr class="te-col-toolbar-row">
          {#each alignments as alignment, i (i)}
            <th class:te-col-selected={selectedColumn === i}>
              <div class="te-col-toolbar">
                <button type="button" class="te-col-handle" class:active={selectedColumn === i} aria-pressed={selectedColumn === i} title={$_('markdownEditor.selectColumn')} onclick={() => toggleColumnSelect(i)}>⋮</button>
                <div class="te-align-group" role="group" aria-label={$_('markdownEditor.table')}>
                  <button type="button" class="te-align-btn" class:active={alignment === "left"} title={$_('markdownEditor.alignLeft')} onclick={() => setAlignment(i, "left")}>⯇</button>
                  <button type="button" class="te-align-btn" class:active={alignment === "center"} title={$_('markdownEditor.alignCenter')} onclick={() => setAlignment(i, "center")}>≡</button>
                  <button type="button" class="te-align-btn" class:active={alignment === "right"} title={$_('markdownEditor.alignRight')} onclick={() => setAlignment(i, "right")}>⯈</button>
                </div>
                <button type="button" class="te-col-move-left" title={$_('markdownEditor.moveColumnLeft')} disabled={i === 0} onclick={() => moveColumn(i, -1)}>←</button>
                <button type="button" class="te-col-move-right" title={$_('markdownEditor.moveColumnRight')} disabled={i === headerCells.length - 1} onclick={() => moveColumn(i, 1)}>→</button>
                <button type="button" class="te-col-remove" title={$_('markdownEditor.removeColumn')} disabled={headerCells.length <= 1} onclick={() => removeColumn(i)}>✕</button>
              </div>
            </th>
          {/each}
          <th class="te-actions-col"></th>
        </tr>
      </thead>
      <tbody>
        {#each rows as row, ri (ri)}
          <tr class="te-data-row" class:te-row-selected={selectedRow === ri}>
            {#each row as _cell, ci (ci)}
              <td><input class="te-cell" bind:value={rows[ri][ci]} /></td>
            {/each}
            <td class="te-actions-col">
              <button type="button" class="te-row-handle" class:active={selectedRow === ri} aria-pressed={selectedRow === ri} title={$_('markdownEditor.selectRow')} onclick={() => toggleRowSelect(ri)}>⋮</button>
              <button type="button" class="te-row-move-up" title={$_('markdownEditor.moveRowUp')} disabled={ri === 0} onclick={() => moveRow(ri, -1)}>↑</button>
              <button type="button" class="te-row-move-down" title={$_('markdownEditor.moveRowDown')} disabled={ri === rows.length - 1} onclick={() => moveRow(ri, 1)}>↓</button>
              <button type="button" class="te-row-remove" title={$_('markdownEditor.removeRow')} onclick={() => removeRow(ri)}>✕</button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <div class="te-grid-actions">
    <button type="button" class="te-add-row" onclick={addRow}>+ {$_('markdownEditor.addRow')}</button>
    <button type="button" class="te-insert-row-above" disabled={selectedRow === null} onclick={insertRowAbove}>{$_('markdownEditor.insertRowAbove')}</button>
    <button type="button" class="te-insert-row-below" disabled={selectedRow === null} onclick={insertRowBelow}>{$_('markdownEditor.insertRowBelow')}</button>
    <button type="button" class="te-add-column" onclick={addColumn}>+ {$_('markdownEditor.addColumn')}</button>
    <button type="button" class="te-insert-column-left" disabled={selectedColumn === null} onclick={insertColumnLeft}>{$_('markdownEditor.insertColumnLeft')}</button>
    <button type="button" class="te-insert-column-right" disabled={selectedColumn === null} onclick={insertColumnRight}>{$_('markdownEditor.insertColumnRight')}</button>
  </div>

  {#snippet footer()}
    <Button variant="secondary" onclick={onCancel}>{$_('common.cancel')}</Button>
    <Button variant="primary" onclick={handleConfirm}>{$_('common.save')}</Button>
  {/snippet}
</Modal>

<style>
  .te-grid-scroll { overflow-x: auto; }
  .te-table { border-collapse: collapse; }
  .te-cell {
    width: 120px; box-sizing: border-box;
    font-family: var(--font-sans); font-size: 12px;
    background: var(--surface-alt); color: var(--text);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 5px 7px;
  }
  .te-cell:focus { outline: none; border-color: var(--accent); }
  .te-header-input { font-weight: 600; }
  th, td { padding: 3px; }
  .te-actions-col { width: 24px; padding: 3px 0 3px 4px; }

  .te-align-group { display: inline-flex; gap: 1px; }
  .te-align-btn {
    padding: 2px 6px; font-size: 11px;
    border: 1px solid var(--border); background: none; color: var(--text-muted); cursor: pointer;
  }
  .te-align-btn:first-child { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }
  .te-align-btn:last-child { border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
  .te-align-btn.active { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); }

  .te-row-remove, .te-col-remove,
  .te-row-handle, .te-col-handle,
  .te-row-move-up, .te-row-move-down,
  .te-col-move-left, .te-col-move-right {
    width: 20px; height: 20px; padding: 0; font-size: 10px; line-height: 1;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: none; color: var(--text-muted); cursor: pointer;
  }
  .te-row-remove:hover, .te-col-remove:hover:not(:disabled) { background: var(--danger); color: white; border-color: var(--danger); }
  .te-col-remove:disabled, .te-row-move-up:disabled, .te-row-move-down:disabled,
  .te-col-move-left:disabled, .te-col-move-right:disabled { opacity: 0.35; cursor: default; }
  .te-row-handle:hover, .te-col-handle:hover,
  .te-row-move-up:hover:not(:disabled), .te-row-move-down:hover:not(:disabled),
  .te-col-move-left:hover:not(:disabled), .te-col-move-right:hover:not(:disabled) {
    background: var(--surface-hover); color: var(--text);
  }
  .te-row-handle.active, .te-col-handle.active { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); }

  .te-col-toolbar { display: flex; align-items: center; gap: 2px; flex-wrap: wrap; }
  tr.te-row-selected, th.te-col-selected { background: var(--surface-hover); }

  .te-grid-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); }
  .te-add-row, .te-add-column,
  .te-insert-row-above, .te-insert-row-below,
  .te-insert-column-left, .te-insert-column-right {
    font-family: var(--font-sans); font-size: 12px; font-weight: 600;
    padding: 5px 10px; border: 1px solid var(--border); border-radius: var(--radius-md);
    background: var(--surface); color: var(--text-muted); cursor: pointer;
  }
  .te-add-row:hover, .te-add-column:hover,
  .te-insert-row-above:hover:not(:disabled), .te-insert-row-below:hover:not(:disabled),
  .te-insert-column-left:hover:not(:disabled), .te-insert-column-right:hover:not(:disabled) {
    background: var(--surface-hover); color: var(--text);
  }
  .te-insert-row-above:disabled, .te-insert-row-below:disabled,
  .te-insert-column-left:disabled, .te-insert-column-right:disabled { opacity: 0.35; cursor: default; }
</style>
