import { expect, test } from "@playwright/test";

test("customer consultation and reliability evaluation are demonstrable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Customer Chat" })).toBeVisible();

  await page.locator("form").first().getByRole("button").click();
  await expect(page.getByTestId("customer-authenticated")).toBeVisible();

  await page.getByTestId("send-message").click();
  await expect(page.locator(".success").filter({ hasText: "delivery-delay policy" })).toBeVisible();

  await page.getByRole("link", { name: "Metrics" }).click();
  await expect(page.getByRole("heading", { name: "Reliability metrics" })).toBeVisible();
  await page.getByTestId("run-evaluation").click();
  await expect(page.getByRole("heading", { name: /SLO/ })).toContainText("healthy", {
    timeout: 30_000,
  });
});
