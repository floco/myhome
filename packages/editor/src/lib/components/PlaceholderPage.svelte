<script lang="ts">
  interface Props {
    icon: string;
    label: string;
    description: string;
  }
  let { icon, label, description }: Props = $props();
</script>

<div class="placeholder">
  <div class="icon">{icon}</div>
  <h2 class="label">{label}</h2>
  <p class="desc">{description}</p>
  <span class="badge">Coming soon</span>
</div>

<style>
  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--text-muted);
    padding: 40px;
    text-align: center;
  }
  .icon { font-size: 48px; line-height: 1; }
  .label { font-size: 20px; font-weight: 600; color: var(--text); margin: 0; }
  .desc { font-size: 14px; max-width: 360px; margin: 0; }
  .badge {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 3px 10px;
    border-radius: var(--radius-pill);
    background: var(--surface-hover);
    color: var(--text-muted);
  }
</style>
