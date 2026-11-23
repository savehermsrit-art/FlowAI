import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";
const stamp = Date.now();
async function signIn(page: Page, role = "citizen", name = `e2e-${stamp}`) {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Find my schemes", exact: true })
    .last()
    .click();
  await page.getByLabel("Demo username").fill(name);
  await page
    .getByRole("combobox", { name: "I am a", exact: true })
    .selectOption(role);
  if (role === "admin")
    await page
      .getByLabel("Local admin access key")
      .fill(
        fs
          .readFileSync(
            path.join(process.cwd(), "../data/admin-access.txt"),
            "utf8",
          )
          .trim(),
      );
  await page.getByRole("button", { name: "Get a one-time code" }).click();
  const code = await page.getByTestId("development-code").textContent();
  await page.getByLabel("One-time code", { exact: true }).fill(code!.trim());
  await page.getByRole("button", { name: "Continue securely" }).click();
  await expect(
    page.getByRole("heading", {
      name:
        role === "admin"
          ? "Review before any rule changes."
          : "Your support, one step at a time.",
    }),
  ).toBeVisible();
}
async function consentAndLoad(page: Page, c = "A") {
  await page
    .getByRole("button", {
      name:
        c === "A"
          ? "A · Complete evidence"
          : c === "B"
            ? "B · Missing income"
            : "C · Age condition fails",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("button", { name: "Give consent & continue" }),
  ).toBeDisabled();
  await page.getByLabel("I have read this notice").check();
  await page.getByRole("button", { name: "Give consent & continue" }).click();
  await page
    .getByRole("button", {
      name: "Load fictional sample documents",
      exact: true,
    })
    .click();
  await expect(page.getByText("Ready to review", { exact: true })).toHaveCount(
    c === "B" ? 2 : 3,
    { timeout: 60000 },
  );
  await page
    .getByRole("button", { name: "View document", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("img")).toBeVisible();
  await expect
    .poll(() =>
      dialog
        .getByRole("img")
        .evaluate(
          (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
        ),
    )
    .toBeTruthy();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await page
    .getByRole("button", { name: "Review evidence", exact: true })
    .last()
    .click();
  await page
    .getByRole("button", { name: "Confirm all unchanged fields" })
    .click();
  await expect(page.getByText("Confirmed by you", { exact: true })).toHaveCount(
    c === "B" ? 2 : 3,
  );
  await page.getByRole("button", { name: "Assess my options" }).click();
}
test("landing is accessible and responsive, and Kannada renders", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
  await page.screenshot({
    path: "../data/landing-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Language", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "kn");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "ಮಾರ್ಗದರ್ಶನ",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../data/landing-mobile-kn.png",
    fullPage: true,
  });
});
for (const [c, verdict] of [
  ["A", "Likely eligible"],
  ["B", "Needs more evidence"],
  ["C", "Not eligible"],
])
  test(`complete citizen document journey ${c} → ${verdict}`, async ({
    page,
  }) => {
    await signIn(page, "citizen", `e2e-${stamp}-${c}`);
    await consentAndLoad(page, c);
    await expect(page.getByTestId("verdict")).toHaveText([verdict, verdict]);
    await expect(
      page.getByText("Source clause demo:age", { exact: true }),
    ).toHaveCount(2);
    await expect(
      page.getByText("Additional application documents", { exact: true }),
    ).toHaveCount(2);
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("link", { name: "Download report & checklist" })
      .click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("FormFlow");
    await download.saveAs(`../data/browser-report-${c}.pdf`);
    if (c === "A") {
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(results.violations).toEqual([]);
      await page.screenshot({
        path: "../data/results-desktop.png",
        fullPage: true,
      });
      await page
        .getByRole("button", { name: "Previous assessments", exact: true })
        .click();
      await page
        .getByRole("button", { name: "View assessment", exact: true })
        .first()
        .click();
      await expect(page.getByTestId("verdict")).toHaveText([verdict, verdict]);
    }
    await page
      .getByRole("button", { name: "Privacy & data", exact: true })
      .last()
      .click();
    page.once("dialog", (dialog) => dialog.accept());
    await page
      .getByRole("button", { name: "Delete this profile and its data" })
      .click();
    await expect(
      page.getByRole("heading", { name: "Your support, one step at a time." }),
    ).toBeVisible();
  });
test("scanned image runs real local OCR and unauthorized caregiver is denied", async ({
  page,
  browser,
}) => {
  await signIn(page, "caregiver", `carer-${stamp}`);
  await page.getByLabel("I am authorized to assist").check();
  await page
    .getByRole("button", { name: "A · Complete evidence", exact: true })
    .click();
  await page.getByLabel("I have read this notice").check();
  await page.getByRole("button", { name: "Give consent & continue" }).click();
  const fixture = await page.request.get(
    "/api/v1/demo/document/A/age_proof?format=png&language=en",
  );
  await page.locator("input[type=file][multiple]").setInputFiles({
    name: "FICTIONAL-scan.png",
    mimeType: "image/png",
    buffer: await fixture.body(),
  });
  await expect(page.getByText("Ready to review", { exact: true })).toHaveCount(
    1,
    { timeout: 60000 },
  );
  const profiles = await (await page.request.get("/api/v1/profiles")).json();
  const id = profiles[profiles.length - 1].id;
  const facts = await (
    await page.request.get(`/api/v1/profiles/${id}/facts`)
  ).json();
  expect(
    facts.some((f: { method: string }) => f.method === "tesseract_eng_kan"),
  ).toBeTruthy();
  expect(facts.find((f: { key: string }) => f.key === "age").value).toBe("70");
  const context = await browser.newContext();
  const outsider = await context.newPage();
  await signIn(outsider, "caregiver", `other-carer-${stamp}`);
  expect(
    (await outsider.request.get(`/api/v1/profiles/${id}/facts`)).status(),
  ).toBe(404);
  expect((await outsider.request.get("/api/v1/admin/overview")).status()).toBe(
    403,
  );
  await context.close();
});
test("administrator approves a validated source proposal and rejects another", async ({
  page,
}) => {
  await signIn(page, "admin", `admin-${stamp}`);
  await page
    .getByRole("button", { name: "Simulate a fictional source change" })
    .click();
  await expect(
    page.getByText("Pending review", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Validate & approve" })
    .first()
    .click();
  await expect(
    page.getByText("Approved", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Simulate a fictional source change" })
    .click();
  await page
    .getByRole("button", { name: "Reject", exact: true })
    .first()
    .click();
  await expect(
    page.getByText("Rejected", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run synthetic evaluation" }).click();
  await expect(
    page.locator("pre").filter({ hasText: "scheme_accuracy" }),
  ).toContainText('"scheme_accuracy": 1');
});
test("Kannada citizen journey reaches explanations and a Kannada report", async ({
  page,
}) => {
  await signIn(page, "citizen", `kannada-${stamp}`);
  await page.getByRole("button", { name: "Language", exact: true }).click();
  await page
    .getByRole("button", { name: "A · ಸಂಪೂರ್ಣ ದಾಖಲೆ", exact: true })
    .click();
  await page.getByLabel("ಈ ಸೂಚನೆಯನ್ನು ಓದಿ").check();
  await page.getByRole("button", { name: "ಸಮ್ಮತಿ ನೀಡಿ ಮುಂದುವರಿಯಿರಿ" }).click();
  await page
    .getByRole("button", { name: "ಕಾಲ್ಪನಿಕ ಮಾದರಿ ದಾಖಲೆಗಳನ್ನು ಸೇರಿಸಿ", exact: true })
    .click();
  await expect(page.getByText("ಪರಿಶೀಲನೆಗೆ ಸಿದ್ಧ", { exact: true })).toHaveCount(3, {
    timeout: 60000,
  });
  await page
    .getByRole("button", { name: "ಮಾಹಿತಿ ಪರಿಶೀಲನೆ", exact: true })
    .last()
    .click();
  await page
    .getByRole("button", { name: "ಬದಲಾಗದ ಎಲ್ಲ ಮಾಹಿತಿಯನ್ನು ದೃಢೀಕರಿಸಿ" })
    .click();
  await expect(page.getByText("ನೀವು ದೃಢೀಕರಿಸಿದ್ದೀರಿ", { exact: true })).toHaveCount(
    3,
  );
  await page.getByRole("button", { name: "ನನ್ನ ಆಯ್ಕೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ" }).click();
  await expect(page.getByTestId("verdict")).toHaveText([
    "ಅರ್ಹರಾಗಿರುವ ಸಾಧ್ಯತೆ",
    "ಅರ್ಹರಾಗಿರುವ ಸಾಧ್ಯತೆ",
  ]);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "ವರದಿ ಮತ್ತು ದಾಖಲೆ ಪಟ್ಟಿ ಡೌನ್‌ಲೋಡ್" }).click();
  const download = await downloadPromise;
  await download.saveAs("../data/browser-report-kn.pdf");
  await page.screenshot({
    path: "../data/results-kannada.png",
    fullPage: true,
  });
});
