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
  if (diffDays < -1) return `${Math.abs(diffDays)}d overdue`;
  if (diffDays === -1) return "Yesterday";
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays <= 7) return `In ${diffDays}d`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
