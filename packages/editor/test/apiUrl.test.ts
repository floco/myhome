import { describe, it, expect, afterEach } from "vitest";
import { apiUrl, wsUrl } from "../src/lib/apiUrl";

function setBaseURI(url: string): void {
  Object.defineProperty(document, "baseURI", { value: url, configurable: true });
}

afterEach(() => {
  setBaseURI("http://localhost:3000/");
});

describe("apiUrl", () => {
  it("returns the path unchanged when served from domain root", () => {
    setBaseURI("http://localhost:3000/");
    expect(apiUrl("/api/homes")).toBe("/api/homes");
  });

  it("rewrites relative to the document base when served from a path prefix", () => {
    setBaseURI("http://localhost:3000/api/hassio_ingress/abc123/");
    expect(apiUrl("/api/homes")).toBe("http://localhost:3000/api/hassio_ingress/abc123/api/homes");
  });

  it("preserves nested paths and query strings under a prefix", () => {
    setBaseURI("http://localhost:3000/api/hassio_ingress/abc123/");
    expect(apiUrl("/api/homes/h1/kb/e1?x=1")).toBe(
      "http://localhost:3000/api/hassio_ingress/abc123/api/homes/h1/kb/e1?x=1",
    );
  });

  it("leaves non-absolute paths untouched", () => {
    setBaseURI("http://localhost:3000/api/hassio_ingress/abc123/");
    expect(apiUrl("relative/path")).toBe("relative/path");
  });
});

describe("wsUrl", () => {
  it("converts http to ws at domain root", () => {
    setBaseURI("http://localhost:3000/");
    expect(wsUrl("/api/ha/ws")).toBe("ws://localhost:3000/api/ha/ws");
  });

  it("converts https to wss under an ingress path prefix", () => {
    setBaseURI("https://localhost:3000/api/hassio_ingress/abc123/");
    expect(wsUrl("/api/ha/ws")).toBe("wss://localhost:3000/api/hassio_ingress/abc123/api/ha/ws");
  });
});
