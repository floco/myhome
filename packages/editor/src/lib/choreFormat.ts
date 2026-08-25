import { _ } from "svelte-i18n";
import { get } from "svelte/store";
import type { Chore, Assignment } from "./choreStore.svelte";
import { formatDate } from "./dateFormat";

export function displayName(chore: Chore): string {
  let name = chore.name.trim();
  if (chore.emoji && name.startsWith(chore.emoji)) name = name.slice(chore.emoji.length).trim();
  return name;
}

// A chore's own `nextDueDate` only tracks the chore-level "complete all"
// action; completing a single room assignment only advances that
// assignment's `nextDueDate`. The earliest assignment due date is what the
// chores list actually displays, so anywhere that needs to show/preview a
// chore's real next-due must use this instead of `chore.nextDueDate` once
// the chore has assignments.
export function earliestDue(chore: Chore, assignments: Assignment[]): string {
  const dates = assignments.map((a) => a.nextDueDate).filter(Boolean).sort();
  return dates[0] ?? chore.nextDueDate;
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
  return formatDate(d);
}
