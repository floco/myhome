<!-- packages/editor/src/lib/components/settings/SettingsBackup.svelte -->
<script lang="ts">
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";
  import Modal from "../ui/Modal.svelte";
  import SortableTable from "../ui/SortableTable.svelte";
  import type { Column } from "../ui/SortableTable.types";

  let downloadingBackup = $state(false);
  let backupError = $state<string | null>(null);
  let restoreFile = $state<File | null>(null);
  let showRestoreConfirm = $state(false);
  let restoringBackup = $state(false);
  let restoreSuccess = $state(false);
  let restoreError = $state<string | null>(null);
  let fileInputEl: HTMLInputElement | undefined = $state();

  async function downloadBackup(): Promise<void> {
    downloadingBackup = true;
    backupError = null;
    restoreSuccess = false;
    try {
      const resp = await fetch("/api/backup/download");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const disposition = resp.headers.get("content-disposition") ?? "";
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match ? match[1] : "myhome-backup.zip";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      backupError = "Backup failed. Please try again.";
    } finally {
      downloadingBackup = false;
    }
  }

  function onFileSelected(e: Event): void {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    restoreFile = file;
    restoreError = null;
    restoreSuccess = false;
    showRestoreConfirm = true;
  }

  async function confirmRestore(): Promise<void> {
    if (!restoreFile) return;
    restoringBackup = true;
    restoreError = null;
    try {
      const form = new FormData();
      form.append("file", restoreFile);
      const resp = await fetch("/api/backup/restore", { method: "POST", body: form });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        const msg = (data as { detail?: string }).detail ?? `HTTP ${resp.status}`;
        throw new Error(msg);
      }
      restoreSuccess = true;
      showRestoreConfirm = false;
    } catch (e) {
      restoreError = e instanceof Error ? e.message : "Restore failed.";
    } finally {
      restoringBackup = false;
      restoreFile = null;
      if (fileInputEl) fileInputEl.value = "";
    }
  }

  function cancelRestore(): void {
    showRestoreConfirm = false;
    restoreFile = null;
    restoreError = null;
    if (fileInputEl) fileInputEl.value = "";
  }

  interface ScheduledBackupConfig {
    enabled: boolean;
    frequency: "daily" | "weekly" | "monthly";
    time: string;
    dayOfWeek: number;
    dayOfMonth: number;
    retentionCount: number;
  }
  interface ScheduledBackupEntry {
    filename: string;
    createdAt: string;
    sizeBytes: number;
  }

  function defaultBackupConfig(): ScheduledBackupConfig {
    return { enabled: false, frequency: "daily", time: "03:00", dayOfWeek: 7, dayOfMonth: 1, retentionCount: 7 };
  }

  const WEEKDAY_OPTIONS = [
    { value: 1, label: "Monday" }, { value: 2, label: "Tuesday" }, { value: 3, label: "Wednesday" },
    { value: 4, label: "Thursday" }, { value: 5, label: "Friday" }, { value: 6, label: "Saturday" },
    { value: 7, label: "Sunday" },
  ];

  let scheduledConfig = $state<ScheduledBackupConfig>(defaultBackupConfig());
  let scheduledConfigLoaded = $state(false);
  let scheduledConfigError = $state<string | null>(null);
  let scheduledConfigSaving = $state(false);
  let scheduledDayOfMonthStr = $state(String(defaultBackupConfig().dayOfMonth));
  let scheduledRetentionCountStr = $state(String(defaultBackupConfig().retentionCount));
  let scheduledBackups = $state<ScheduledBackupEntry[]>([]);
  let runningBackupNow = $state(false);
  let confirmDeleteBackupFilename = $state<string | null>(null);

  async function loadScheduledBackupConfig(): Promise<void> {
    const resp = await fetch("/api/backup/config");
    if (resp.ok) {
      scheduledConfig = await resp.json();
      scheduledDayOfMonthStr = String(scheduledConfig.dayOfMonth);
      scheduledRetentionCountStr = String(scheduledConfig.retentionCount);
    }
    scheduledConfigLoaded = true;
  }

  async function loadScheduledBackups(): Promise<void> {
    const resp = await fetch("/api/backup/scheduled");
    if (resp.ok) scheduledBackups = await resp.json();
  }

  loadScheduledBackupConfig();
  loadScheduledBackups();

  async function saveScheduledBackupConfig(): Promise<void> {
    scheduledConfigError = null;
    scheduledConfigSaving = true;
    try {
      const resp = await fetch("/api/backup/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...scheduledConfig,
          dayOfMonth: parseInt(scheduledDayOfMonthStr, 10) || 1,
          retentionCount: parseInt(scheduledRetentionCountStr, 10) || 1,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      scheduledConfig = await resp.json();
      scheduledDayOfMonthStr = String(scheduledConfig.dayOfMonth);
      scheduledRetentionCountStr = String(scheduledConfig.retentionCount);
    } catch (e) {
      scheduledConfigError = e instanceof Error ? e.message : String(e);
    } finally {
      scheduledConfigSaving = false;
    }
  }

  async function runBackupNow(): Promise<void> {
    runningBackupNow = true;
    scheduledConfigError = null;
    try {
      const resp = await fetch("/api/backup/scheduled/run", { method: "POST" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      await loadScheduledBackups();
    } catch (e) {
      scheduledConfigError = e instanceof Error ? e.message : String(e);
    } finally {
      runningBackupNow = false;
    }
  }

  function formatBackupSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function downloadScheduledBackup(filename: string): Promise<void> {
    const resp = await fetch(`/api/backup/scheduled/${filename}/download`);
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function deleteScheduledBackup(filename: string): Promise<void> {
    await fetch(`/api/backup/scheduled/${filename}`, { method: "DELETE" });
    confirmDeleteBackupFilename = null;
    await loadScheduledBackups();
  }
</script>

<Card>
  <div class="section-header">
    <h2>Backup & Restore</h2>
  </div>
  <div class="backup-actions">
    <div class="backup-action">
      <p class="backup-desc">Download a zip archive of all your data.</p>
      <Button onclick={downloadBackup} disabled={downloadingBackup}>
        {downloadingBackup ? "Downloading…" : "Download Backup"}
      </Button>
    </div>
    <div class="backup-action">
      <p class="backup-desc">Replace all current data from a previously downloaded backup.</p>
      <Button variant="secondary" onclick={() => fileInputEl?.click()}>Restore from Backup</Button>
      <input
        bind:this={fileInputEl}
        type="file"
        accept=".zip"
        class="hidden-file-input"
        onchange={onFileSelected}
      />
    </div>
  </div>
  {#if backupError}<div class="error">{backupError}</div>{/if}
  {#if restoreError}<div class="error">{restoreError}</div>{/if}
  {#if restoreSuccess}<div class="success-msg">Restore complete. Reload the page to see updated data.</div>{/if}

  <h3 class="subsection-title" style="margin-top: var(--space-4)">Scheduled Backups</h3>
  {#if scheduledConfigLoaded}
    <label class="module-row">
      <input class="backup-enable-toggle" type="checkbox" bind:checked={scheduledConfig.enabled} />
      <span class="mod-label">Enable scheduled backups</span>
    </label>
    {#if scheduledConfig.enabled}
      <div class="modal-form" style="margin-top: var(--space-3)">
        <div class="modal-field">
          <span class="modal-label">Frequency</span>
          <select bind:value={scheduledConfig.frequency} class="modal-select">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        {#if scheduledConfig.frequency === "weekly"}
          <div class="modal-field">
            <span class="modal-label">Day of week</span>
            <select bind:value={scheduledConfig.dayOfWeek} class="modal-select">
              {#each WEEKDAY_OPTIONS as opt (opt.value)}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </div>
        {/if}
        {#if scheduledConfig.frequency === "monthly"}
          <div class="modal-field">
            <span class="modal-label">Day of month</span>
            <Input type="number" bind:value={scheduledDayOfMonthStr} />
          </div>
        {/if}
        <div class="modal-field">
          <span class="modal-label">Time (UTC, HH:MM)</span>
          <Input bind:value={scheduledConfig.time} placeholder="03:00" />
        </div>
        <div class="modal-field">
          <span class="modal-label">Keep last N backups</span>
          <Input type="number" bind:value={scheduledRetentionCountStr} />
        </div>
      </div>
    {/if}
    {#if scheduledConfigError}<div class="error">{scheduledConfigError}</div>{/if}
    <div class="modal-actions">
      <Button onclick={saveScheduledBackupConfig} disabled={scheduledConfigSaving}>
        {scheduledConfigSaving ? "Saving…" : "Save"}
      </Button>
      <Button variant="secondary" onclick={runBackupNow} disabled={runningBackupNow}>
        {runningBackupNow ? "Running…" : "Run backup now"}
      </Button>
    </div>
  {/if}

  {#if scheduledBackups.length > 0}
    <div class="table-wrapper" style="margin-top: var(--space-3)">
      {#snippet createdCell(backup: ScheduledBackupEntry)}
        {new Date(backup.createdAt).toLocaleString()}
      {/snippet}
      {#snippet sizeCell(backup: ScheduledBackupEntry)}
        {formatBackupSize(backup.sizeBytes)}
      {/snippet}
      {#snippet actionsCell(backup: ScheduledBackupEntry)}
        {#if confirmDeleteBackupFilename === backup.filename}
          <span class="confirm-text">Delete?</span>
          <button class="icon-action danger" onclick={() => deleteScheduledBackup(backup.filename)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteBackupFilename = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => downloadScheduledBackup(backup.filename)} title="Download">⬇</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteBackupFilename = backup.filename; }} title="Delete">🗑</button>
        {/if}
      {/snippet}
      <SortableTable
        columns={[
          { key: "created", label: "Created", sortValue: (b) => new Date(b.createdAt), cell: createdCell },
          { key: "size", label: "Size", sortValue: (b) => b.sizeBytes, cell: sizeCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: actionsCell },
        ] as Column<ScheduledBackupEntry>[]}
        rows={scheduledBackups}
        rowKey={(b) => b.filename}
        rowClass={() => "backup-row"}
      />
    </div>
  {/if}
</Card>

<Modal open={showRestoreConfirm} title="Restore Backup" onclose={cancelRestore} width="400px">
  {#snippet children()}
    <p class="restore-warning">This will replace all current data with the contents of the backup. This cannot be undone.</p>
  {/snippet}
  {#snippet footer()}
    <Button variant="secondary" onclick={cancelRestore}>Cancel</Button>
    <Button onclick={confirmRestore} disabled={restoringBackup}>
      {restoringBackup ? "Restoring…" : "Restore"}
    </Button>
  {/snippet}
</Modal>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }
  .hidden-file-input { display: none; }

  .subsection-title { margin: 0 0 var(--space-2); font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: .05em; }

  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-label { font-size: 13px; color: var(--text); }

  .modal-form { display: flex; flex-direction: column; gap: 14px; }
  .modal-field { display: flex; flex-direction: column; gap: 5px; }
  .modal-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .modal-select { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; color: var(--text); font-size: 0.9rem; font-family: var(--font-sans); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }

  .table-wrapper { overflow-x: auto; }

  :global(.actions) { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
  .icon-action { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; padding: 2px 5px; border-radius: 3px; }
  .icon-action:hover { background: var(--surface-hover); color: var(--text-muted); }
  .icon-action.danger { color: var(--danger); }
  .icon-action.danger:hover { background: color-mix(in srgb, var(--danger) 18%, var(--surface)); }
  .confirm-text { font-size: 10px; color: var(--danger); }
</style>
