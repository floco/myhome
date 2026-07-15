// packages/editor/src/lib/apiUrl.ts
/**
 * Home Assistant's ingress proxy serves this app under a per-install path
 * prefix it controls (e.g. /api/hassio_ingress/<token>/), never at domain
 * root -- but every absolute "/api/..." path in this app's source assumes
 * domain-root deployment. Rewrite those to resolve relative to the current
 * document instead, so they land back under whatever prefix ingress used
 * instead of escaping to Home Assistant's own frontend root. At domain root
 * (dev mode via the vite proxy, or direct non-ingress access) this is a
 * no-op -- the path is returned completely unchanged.
 */
export function apiUrl(path: string): string {
  if (!path.startsWith("/")) return path;
  const base = new URL(document.baseURI);
  if (base.pathname === "/") return path;
  return new URL(path.slice(1), base).toString();
}
