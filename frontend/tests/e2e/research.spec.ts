import { test, expect } from "@playwright/test";

test("official scheme question shows a resolved citation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore schemes" }).first().click();
  await expect(
    page.getByRole("heading", { name: "Sandhya Suraksha Yojana" }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ask about this scheme" })
    .nth(1)
    .click();
  await page
    .getByLabel("Your question")
    .fill("What is the age requirement for Sandhya Suraksha?");
  await page.getByRole("button", { name: "Find answer" }).click();
  await expect(page.locator(".answer-panel > p")).toHaveText(
    "Age 65 years or older",
  );
  const source = page.locator(".answer-panel a").first();
  await expect(source).toHaveAttribute(
    "href",
    "https://dssp.karnataka.gov.in/dssp/Sandhya_Suraksha.aspx",
  );
});

test("Kannada scheme details and answer stay linked to original source", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore schemes" }).first().click();
  await page.getByRole("button", { name: "Language" }).click();
  await page.getByRole("button", { name: "ಈ ಯೋಜನೆಯ ಬಗ್ಗೆ ಕೇಳಿ" }).nth(1).click();
  await page.getByLabel("ನಿಮ್ಮ ಪ್ರಶ್ನೆ").fill("ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಯೋಜನೆಗೆ ಆದಾಯ ಮಿತಿ ಎಷ್ಟು?");
  await page.getByRole("button", { name: "ಉತ್ತರ ಹುಡುಕಿ" }).click();
  await expect(page.locator(".answer-panel")).toContainText("32,000");
  await expect(page.locator(".answer-panel a").first()).toHaveAttribute(
    "href",
    /dssp\.karnataka\.gov\.in/,
  );
});
