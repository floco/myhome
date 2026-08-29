<!-- packages/editor/src/lib/components/ui/TableEditorModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Modal from "./Modal.svelte";
  import Button from "./Button.svelte";
  import Popover from "./Popover.svelte";
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

  let openRowMenu = $state<number | null>(null);
  let openColumnMenu = $state<number | null>(null);
  let menuAnchorEl = $state<HTMLElement | null>(null);

  function closeMenus(): void {
    openRowMenu = null;
    openColumnMenu = null;
    menuAnchorEl = null;
  }

  function showRowMenu(e: MouseEvent, index: number): void {
    menuAnchorEl = e.currentTarget as HTMLElement;
    openColumnMenu = null;
    openRowMenu = openRowMenu === index ? null : index;
  }

  function showColumnMenu(e: MouseEvent, index: number): void {
    menuAnchorEl = e.currentTarget as HTMLElement;
    openRowMenu = null;
    openColumnMenu = openColumnMenu === index ? null : index;
  }

  function addRow(): void {
    rows = [...rows, headerCells.map(() => "")];
  }

  function removeRow(index: number): void {
    rows = rows.filter((_, i) => i !== index);
    closeMenus();
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
    closeMenus();
  }

  function setAlignment(index: number, alignment: Alignment): void {
    alignments = alignments.map((a, i) => (i === index ? alignment : a));
    closeMenus();
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
    closeMenus();
  }

  function moveColumn(index: number, delta: number): void {
    const target = index + delta;
    if (target < 0 || target >= headerCells.length) return;
    headerCells = swap(headerCells, index, target);
    alignments = swap(alignments, index, target);
    rows = rows.map((row) => swap(row, index, target));
    closeMenus();
  }

  function insertRowAbove(index: number): void {
    rows = [...rows.slice(0, index), headerCells.map(() => ""), ...rows.slice(index)];
    closeMenus();
  }

  function insertRowBelow(index: number): void {
    const at = index + 1;
    rows = [...rows.slice(0, at), headerCells.map(() => ""), ...rows.slice(at)];
    closeMenus();
  }

  function insertColumn(at: number): void {
    headerCells = [...headerCells.slice(0, at), "", ...headerCells.slice(at)];
    alignments = [...alignments.slice(0, at), "left", ...alignments.slice(at)];
    rows = rows.map((row) => [...row.slice(0, at), "", ...row.slice(at)]);
    closeMenus();
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
            <th>
              <div class="te-header-cell">
                <input class="te-cell te-header-input" bind:value={headerCells[i]} />
                <button type="button" class="te-col-menu-btn" title={$_('markdownEditor.columnActions')} onclick={(e) => showColumnMenu(e, i)}>⋮</button>
              </div>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as row, ri (ri)}
          <tr class="te-data-row">
            {#each row as _cell, ci (ci)}
              <td><input class="te-cell" bind:value={rows[ri][ci]} /></td>
            {/each}
            <td class="te-actions-col">
              <button type="button" class="te-row-menu-btn" title={$_('markdownEditor.rowActions')} onclick={(e) => showRowMenu(e, ri)}>⋮</button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <div class="te-grid-actions">
    <button type="button" class="te-add-row" onclick={addRow}>+ {$_('markdownEditor.addRow')}</button>
    <button type="button" class="te-add-column" onclick={addColumn}>+ {$_('markdownEditor.addColumn')}</button>
  </div>

  <Popover open={openRowMenu !== null} anchorEl={menuAnchorEl} onclose={closeMenus} width={180}>
    {#if openRowMenu !== null}
      <button type="button" class="te-menu-item te-menu-move-up" disabled={openRowMenu === 0} onclick={() => moveRow(openRowMenu!, -1)}>↑ {$_('markdownEditor.moveRowUp')}</button>
      <button type="button" class="te-menu-item te-menu-move-down" disabled={openRowMenu === rows.length - 1} onclick={() => moveRow(openRowMenu!, 1)}>↓ {$_('markdownEditor.moveRowDown')}</button>
      <div class="te-menu-sep"></div>
      <button type="button" class="te-menu-item te-menu-insert-above" onclick={() => insertRowAbove(openRowMenu!)}>{$_('markdownEditor.insertRowAbove')}</button>
      <button type="button" class="te-menu-item te-menu-insert-below" onclick={() => insertRowBelow(openRowMenu!)}>{$_('markdownEditor.insertRowBelow')}</button>
      <div class="te-menu-sep"></div>
      <button type="button" class="te-menu-item te-menu-delete-row te-menu-danger" onclick={() => removeRow(openRowMenu!)}>🗑 {$_('markdownEditor.removeRow')}</button>
    {/if}
  </Popover>

  <Popover open={openColumnMenu !== null} anchorEl={menuAnchorEl} onclose={closeMenus} width={200}>
    {#if openColumnMenu !== null}
      <button type="button" class="te-menu-item te-menu-align-left" class:active={alignments[openColumnMenu] === "left"} onclick={() => setAlignment(openColumnMenu!, "left")}>⯇ {$_('markdownEditor.alignLeft')}</button>
      <button type="button" class="te-menu-item te-menu-align-center" class:active={alignments[openColumnMenu] === "center"} onclick={() => setAlignment(openColumnMenu!, "center")}>≡ {$_('markdownEditor.alignCenter')}</button>
      <button type="button" class="te-menu-item te-menu-align-right" class:active={alignments[openColumnMenu] === "right"} onclick={() => setAlignment(openColumnMenu!, "right")}>⯈ {$_('markdownEditor.alignRight')}</button>
      <div class="te-menu-sep"></div>
      <button type="button" class="te-menu-item te-menu-move-left" disabled={openColumnMenu === 0} onclick={() => moveColumn(openColumnMenu!, -1)}>← {$_('markdownEditor.moveColumnLeft')}</button>
      <button type="button" class="te-menu-item te-menu-move-right" disabled={openColumnMenu === headerCells.length - 1} onclick={() => moveColumn(openColumnMenu!, 1)}>→ {$_('markdownEditor.moveColumnRight')}</button>
      <div class="te-menu-sep"></div>
      <button type="button" class="te-menu-item te-menu-insert-left" onclick={() => insertColumn(openColumnMenu!)}>{$_('markdownEditor.insertColumnLeft')}</button>
      <button type="button" class="te-menu-item te-menu-insert-right" onclick={() => insertColumn(openColumnMenu! + 1)}>{$_('markdownEditor.insertColumnRight')}</button>
      <div class="te-menu-sep"></div>
      <button type="button" class="te-menu-item te-menu-delete-column te-menu-danger" disabled={headerCells.length <= 1} onclick={() => removeColumn(openColumnMenu!)}>🗑 {$_('markdownEditor.removeColumn')}</button>
    {/if}
  </Popover>

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

  .te-header-cell { display: flex; align-items: center; gap: 2px; }
  .te-header-cell .te-cell { flex: 1; min-width: 0; }

  .te-row-menu-btn, .te-col-menu-btn {
    width: 20px; height: 20px; padding: 0; font-size: 12px; line-height: 1; flex-shrink: 0;
    border: 1px solid transparent; border-radius: var(--radius-sm);
    background: none; color: var(--text-muted); cursor: pointer;
  }
  .te-row-menu-btn:hover, .te-col-menu-btn:hover { background: var(--surface-hover); color: var(--text); border-color: var(--border); }

  .te-menu-item {
    display: block; width: 100%; text-align: left;
    font-family: var(--font-sans); font-size: 12px;
    padding: 6px 8px; border: none; border-radius: var(--radius-sm);
    background: none; color: var(--text); cursor: pointer;
  }
  .te-menu-item:hover:not(:disabled) { background: var(--surface-hover); }
  .te-menu-item:disabled { opacity: 0.4; cursor: default; }
  .te-menu-item.active { background: var(--accent); color: var(--accent-contrast); }
  .te-menu-item.te-menu-danger { color: var(--danger); }
  .te-menu-sep { height: 1px; background: var(--border); margin: 4px 2px; }

  .te-grid-actions { display: flex; gap: var(--space-2); margin-top: var(--space-3); }
  .te-add-row, .te-add-column {
    font-family: var(--font-sans); font-size: 12px; font-weight: 600;
    padding: 5px 10px; border: 1px solid var(--border); border-radius: var(--radius-md);
    background: var(--surface); color: var(--text-muted); cursor: pointer;
  }
  .te-add-row:hover, .te-add-column:hover { background: var(--surface-hover); color: var(--text); }
</style>
