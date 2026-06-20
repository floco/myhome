// Polyfill ResizeObserver for jsdom environment
(globalThis as any).ResizeObserver = class ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Preserve raw style strings for getAttribute("style")
// jsdom normalizes CSS via cssText setter (adds spaces after colons), but tests
// expect the exact string as written. We store the raw value and return it from getAttribute.
if (typeof window !== "undefined" && window.CSSStyleDeclaration) {
  const proto = window.CSSStyleDeclaration.prototype;
  const origDesc = Object.getOwnPropertyDescriptor(proto, "cssText");
  if (origDesc?.set) {
    const rawStyleMap = new WeakMap<CSSStyleDeclaration, string>();
    Object.defineProperty(proto, "cssText", {
      ...origDesc,
      set(value: string) {
        rawStyleMap.set(this, value);
        origDesc.set!.call(this, value);
      },
    });
    const origGetAttribute = Element.prototype.getAttribute;
    Element.prototype.getAttribute = function (name: string): string | null {
      if (name === "style") {
        const style = (this as HTMLElement).style;
        if (style && rawStyleMap.has(style)) {
          return rawStyleMap.get(style)!;
        }
      }
      return origGetAttribute.call(this, name);
    };
  }
}
