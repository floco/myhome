const STORAGE_PREFIX = "myhome-kb-last-page-";

/** Reads the last-viewed KB page id for a home, or null if none is stored. */
export function getStoredLastPageId(homeId: string): string | null {
  return localStorage.getItem(STORAGE_PREFIX + homeId);
}

/** Persists the last-viewed KB page id for a home. */
export function setStoredLastPageId(homeId: string, pageId: string): void {
  localStorage.setItem(STORAGE_PREFIX + homeId, pageId);
}

/** Clears the stored last-viewed page id for a home (e.g. after it's deleted). */
export function clearStoredLastPageId(homeId: string): void {
  localStorage.removeItem(STORAGE_PREFIX + homeId);
}
