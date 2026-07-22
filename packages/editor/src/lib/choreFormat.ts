import { _ } from "svelte-i18n";
import { get } from "svelte/store";
import type { Chore } from "./choreStore.svelte";

export function displayName(chore: Chore): string {
  let name = chore.name.trim();
  if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
  return name;
}

export function formatDue(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.round((d.getTime() - now.getTime()) / 86400000);
  const t = get(_);
  if (diffDays < -1) return t("chores.dueLabel.overdue", { values: { n: Math.abs(diffDays) } });
  if (diffDays === -1) return t("chores.dueLabel.yesterday");
  if (diffDays === 0) return t("chores.dueLabel.today");
  if (diffDays === 1) return t("chores.dueLabel.tomorrow");
  if (diffDays <= 7) return t("chores.dueLabel.inDays", { values: { n: diffDays } });
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
