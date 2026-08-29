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

  function addRow(): void {
    rows = [...rows, headerCells.map(() => "")];
  }

  function removeRow(index: number): void {
    rows = rows.filter((_, i) => i !== index);
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
  }

  function setAlignment(index: number, alignment: Alignment): void {
    alignments = alignments.map((a, i) => (i === index ? alignment : a));
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
        <tr class="te-align-row">
          {#each alignments as alignment, i (i)}
            <th>
              <div class="te-align-group" role="group" aria-label={$_('markdownEditor.table')}>
                <button type="button" class="te-align-btn" class:active={alignment === "left"} title={$_('markdownEditor.alignLeft')} onclick={() => setAlignment(i, "left")}>⯇</button>
                <button type="button" class="te-align-btn" class:active={alignment === "center"} title={$_('markdownEditor.alignCenter')} onclick={() => setAlignment(i, "center")}>≡</button>
                <button type="button" class="te-align-btn" class:active={alignment === "right"} title={$_('markdownEditor.alignRight')} onclick={() => setAlignment(i, "right")}>⯈</button>
              </div>
            </th>
          {/each}
          <th class="te-actions-col"></th>
        </tr>
      </thead>
      <tbody>
        {#each rows as row, ri (ri)}
          <tr class="te-data-row">
            {#each row as _cell, ci (ci)}
              <td><input class="te-cell" bind:value={rows[ri][ci]} /></td>
            {/each}
            <td class="te-actions-col">
              <button type="button" class="te-row-remove" title={$_('markdownEditor.removeRow')} onclick={() => removeRow(ri)}>✕</button>
            </td>
          </tr>
        {/each}
        <tr class="te-col-remove-row">
          {#each headerCells as _cell, i (i)}
            <td>
              <button type="button" class="te-col-remove" title={$_('markdownEditor.removeColumn')} disabled={headerCells.length <= 1} onclick={() => removeColumn(i)}>✕</button>
            </td>
          {/each}
          <td class="te-actions-col"></td>
        </tr>
      </tbody>
    </table>
  </div>
  <div class="te-grid-actions">
    <button type="button" class="te-add-row" onclick={addRow}>+ {$_('markdownEditor.addRow')}</button>
    <button type="button" class="te-add-column" onclick={addColumn}>+ {$_('markdownEditor.addColumn')}</button>
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

  .te-row-remove, .te-col-remove {
    width: 20px; height: 20px; padding: 0; font-size: 10px; line-height: 1;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: none; color: var(--text-muted); cursor: pointer;
  }
  .te-row-remove:hover, .te-col-remove:hover:not(:disabled) { background: var(--danger); color: white; border-color: var(--danger); }
  .te-col-remove:disabled { opacity: 0.35; cursor: default; }

  .te-grid-actions { display: flex; gap: var(--space-2); margin-top: var(--space-3); }
  .te-add-row, .te-add-column {
    font-family: var(--font-sans); font-size: 12px; font-weight: 600;
    padding: 5px 10px; border: 1px solid var(--border); border-radius: var(--radius-md);
    background: var(--surface); color: var(--text-muted); cursor: pointer;
  }
  .te-add-row:hover, .te-add-column:hover { background: var(--surface-hover); color: var(--text); }
</style>
