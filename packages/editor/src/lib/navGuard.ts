export type NavGuardFn = () => Promise<boolean>;

let activeGuard: NavGuardFn | null = null;

/** Registers the single active nav guard (only one top-level module is ever mounted at a time). */
export function setNavGuard(fn: NavGuardFn | null): void {
  activeGuard = fn;
}

export function getNavGuard(): NavGuardFn | null {
  return activeGuard;
}

export interface GuardedHashRouterOptions {
  getHash: () => string;
  setHash: (hash: string) => void;
  onRoute: (hash: string) => void;
}

/**
 * Wraps hash-change handling so that, when a guard is registered, a route
 * change is provisionally reverted while the guard runs (e.g. flushing a
 * pending autosave); on success the originally-attempted route is replayed,
 * on failure the app stays on the current route.
 */
export function createGuardedHashRouter(opts: GuardedHashRouterOptions): { handleHashChange: () => void } {
  let currentRoute = opts.getHash();
  let suppress = false;

  function handleHashChange(): void {
    const newHash = opts.getHash();

    if (suppress) {
      suppress = false;
      currentRoute = newHash;
      opts.onRoute(newHash);
      return;
    }

    if (newHash === currentRoute) {
      opts.onRoute(newHash);
      return;
    }

    const guard = getNavGuard();
    if (!guard) {
      currentRoute = newHash;
      opts.onRoute(newHash);
      return;
    }

    const attempted = newHash;
    const previous = currentRoute;
    suppress = true;
    opts.setHash(previous);
    guard().then((ok) => {
      if (ok) {
        suppress = true;
        opts.setHash(attempted);
      }
    });
  }

  return { handleHashChange };
}
