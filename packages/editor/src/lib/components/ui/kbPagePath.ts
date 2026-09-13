import type { KBEntry } from "../../kbStore.svelte";

/** Breadcrumb path for a page, e.g. "Kitchen › Appliances › Fridge manual". */
export function kbPagePath(entries: KBEntry[], entry: KBEntry): string {
  const parts: string[] = [entry.title];
  let current = entry.parentId;
  const seen = new Set<string>();
  while (current && !seen.has(current)) {
    seen.add(current);
    const parent = entries.find((e) => e.id === current);
    if (!parent) break;
    parts.unshift(parent.title);
    current = parent.parentId;
  }
  return parts.join(" › ");
}
