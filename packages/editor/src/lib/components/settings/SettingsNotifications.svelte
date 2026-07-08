<!-- packages/editor/src/lib/components/settings/SettingsNotifications.svelte -->
<script lang="ts">
  import type { createSettingsStore } from "../../settingsStore.svelte";
  import Button from "../ui/Button.svelte";
  import Input from "../ui/Input.svelte";
  import Card from "../ui/Card.svelte";

  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: SettingsStore;
  }
  let { store }: Props = $props();

  let notifDraft = $state({ ...store.notificationSettings, haNotifyService: store.notificationSettings.haNotifyService ?? "" });
  let notifChoresThresholdStr = $state(String(store.notificationSettings.choresDueSoonThreshold));
  let notifWarrantyDaysStr = $state(String(store.notificationSettings.warrantyDaysThreshold));
  let notifSynced = $state(false);
  let notifError = $state<string | null>(null);
  let notifSaving = $state(false);

  $effect(() => {
    if (store.loaded && !notifSynced) {
      notifDraft = { ...store.notificationSettings, haNotifyService: store.notificationSettings.haNotifyService ?? "" };
      notifChoresThresholdStr = String(store.notificationSettings.choresDueSoonThreshold);
      notifWarrantyDaysStr = String(store.notificationSettings.warrantyDaysThreshold);
      notifSynced = true;
    }
  });

  async function saveNotificationSettings(): Promise<void> {
    notifError = null;
    notifSaving = true;
    try {
      await store.updateNotificationSettings({
        ...notifDraft,
        haNotifyService: notifDraft.haNotifyService.trim() || null,
        choresDueSoonThreshold: parseFloat(notifChoresThresholdStr) || 0,
        warrantyDaysThreshold: parseInt(notifWarrantyDaysStr, 10) || 0,
      });
    } catch (e) {
      notifError = e instanceof Error ? e.message : String(e);
    } finally {
      notifSaving = false;
    }
  }
</script>

<Card>
  <div class="section-header">
    <h2>Notifications</h2>
  </div>
  <p class="section-desc">
    Surface chores due soon, low-stock consumables, and expiring warranties in
    one place, with an optional daily summary pushed to Home Assistant.
  </p>
  <label class="module-row">
    <input class="notif-enable-toggle" type="checkbox" bind:checked={notifDraft.enabled} />
    <span class="mod-label">Enable notification center</span>
  </label>
  {#if notifDraft.enabled}
    <div class="modal-form" style="margin-top: var(--space-3)">
      <div class="modal-field">
        <span class="modal-label">Chores "due soon" threshold (fraction of period remaining)</span>
        <Input type="number" bind:value={notifChoresThresholdStr} />
      </div>
      <div class="modal-field">
        <span class="modal-label">Warranty "expiring soon" window (days)</span>
        <Input type="number" bind:value={notifWarrantyDaysStr} />
      </div>
      <label class="module-row">
        <input type="checkbox" bind:checked={notifDraft.haPushEnabled} />
        <span class="mod-label">Send a daily digest via Home Assistant</span>
      </label>
      {#if notifDraft.haPushEnabled}
        <div class="modal-field">
          <span class="modal-label">HA notify service</span>
          <Input bind:value={notifDraft.haNotifyService} placeholder="e.g. notify.mobile_app_pixel" />
        </div>
        <div class="modal-field">
          <span class="modal-label">Digest time (UTC, HH:MM)</span>
          <Input bind:value={notifDraft.haPushTime} placeholder="08:00" />
        </div>
      {/if}
    </div>
  {/if}
  {#if notifError}<div class="error">{notifError}</div>{/if}
  <div class="modal-actions">
    <Button onclick={saveNotificationSettings} disabled={notifSaving}>{notifSaving ? "Saving…" : "Save"}</Button>
  </div>
</Card>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
  .mod-label { font-size: 13px; color: var(--text); }

  .modal-form { display: flex; flex-direction: column; gap: 14px; }
  .modal-field { display: flex; flex-direction: column; gap: 5px; }
  .modal-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
</style>
