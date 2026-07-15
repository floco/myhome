// packages/editor/src/lib/ingressFetchShim.ts
/**
 * Every fetch() call across this app is written with an absolute "/api/..."
 * path for simplicity. Importing this module (once, at app bootstrap, before
 * anything else has a chance to call fetch) patches window.fetch to rewrite
 * those through apiUrl() -- see that module for why. This has to be a global
 * patch rather than touching each call site because there are ~100 of them
 * across 17 files.
 */
import { apiUrl } from "./apiUrl";

const nativeFetch = window.fetch.bind(window);

window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  if (typeof input === "string") {
    return nativeFetch(apiUrl(input), init);
  }
  return nativeFetch(input, init);
}) as typeof window.fetch;
