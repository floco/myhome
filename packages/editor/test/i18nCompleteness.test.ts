import { describe, it, expect } from "vitest";
import en from "../src/lib/locales/en.json";
import fr from "../src/lib/locales/fr.json";

function flattenKeys(obj: unknown, prefix = ""): string[] {
  if (typeof obj !== "object" || obj === null) return [prefix];
  return Object.entries(obj).flatMap(([k, v]) => flattenKeys(v, prefix ? `${prefix}.${k}` : k));
}

describe("i18n catalog completeness", () => {
  it("en.json and fr.json have exactly the same set of keys", () => {
    const enKeys = new Set(flattenKeys(en));
    const frKeys = new Set(flattenKeys(fr));

    const missingInFr = [...enKeys].filter((k) => !frKeys.has(k));
    const missingInEn = [...frKeys].filter((k) => !enKeys.has(k));

    expect(missingInFr, `keys missing in fr.json: ${missingInFr.join(", ")}`).toEqual([]);
    expect(missingInEn, `keys missing in en.json: ${missingInEn.join(", ")}`).toEqual([]);
  });

  it("no catalog value is an empty string", () => {
    const emptyEn = flattenKeys(en).filter((k) => {
      const v = k.split(".").reduce((o: any, p) => o?.[p], en);
      return typeof v === "string" && v.trim() === "";
    });
    const emptyFr = flattenKeys(fr).filter((k) => {
      const v = k.split(".").reduce((o: any, p) => o?.[p], fr);
      return typeof v === "string" && v.trim() === "";
    });
    expect(emptyEn).toEqual([]);
    expect(emptyFr).toEqual([]);
  });
});
