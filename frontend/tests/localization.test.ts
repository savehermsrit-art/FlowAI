import { describe, it, expect } from "vitest";
import { en, kn, text } from "../app/i18n";
describe("Accessible bilingual labels", () => {
  it("has a Kannada translation for every English key", () => {
    expect(Object.keys(kn).sort()).toEqual(Object.keys(en).sort());
    for (const [key, value] of Object.entries(kn)) {
      expect(value.trim().length, key).toBeGreaterThan(0);
    }
  });
  it("localizes evidence uncertainty and preliminary verdicts", () => {
    for (const key of [
      "likely",
      "needs",
      "notEligible",
      "UNVERIFIED_CORRECTION",
      "CONFLICTING_EVIDENCE",
      "consentText",
      "deleteConfirm",
    ])
      expect(text("kn", key)).toMatch(/[\u0c80-\u0cff]/);
  });
  it("keeps fictional labeling explicit in both languages", () => {
    expect(en.fictional).toContain("Fictional");
    expect(kn.fictional).toContain("ಕಾಲ್ಪನಿಕ");
  });
});
