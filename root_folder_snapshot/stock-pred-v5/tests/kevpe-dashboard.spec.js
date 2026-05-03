import { expect, test } from "@playwright/test";
import path from "node:path";

test.use({ viewport: { width: 1440, height: 900 } });

const smokeSnapshotPath = path.resolve(
  "../stock_rtx4060_unified/reports/kevpe_event_smoke/dashboard_snapshot.json"
);

test("renders operational summary from exported public dashboard snapshot", async ({ page }) => {
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "REC" }).click();

  await expect(page.getByText("ELIGIBLE", { exact: true })).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("ACCUMULATE", { exact: true })).toBeVisible();
  await expect(page.getByText("AUDIT", { exact: true })).toBeVisible();
  await expect(page.getByText("2 EVENTS")).toBeVisible();
  await expect(page.getByText("APPROVAL", { exact: true })).toBeVisible();
  await expect(page.getByText("2 PENDING")).toBeVisible();
  await expect(page.getByText("PROVIDER", { exact: true })).toBeVisible();
  await expect(page.getByText("SUCCESS", { exact: true })).toBeVisible();

  await page.screenshot({
    path: "../stock_rtx4060_unified/reports/kevpe_event_smoke/dashboard_kevpe_badge.png",
    fullPage: true,
  });
});

test("imports KEVPE dashboard snapshot through IMPORT button", async ({ page }) => {
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "REC" }).click();

  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "IMPORT" }).click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(smokeSnapshotPath);

  await expect(page.getByText("IMPORTED · dashboard_snapshot.json")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("KEVPE AMBER")).toBeVisible();
  await expect(page.getByText("E[RV]=-1.3%")).toBeVisible();
  await expect(page.getByText("CI [-3.3, 0.7]")).toBeVisible();
  await expect(page.getByText("AUDIT", { exact: true })).toBeVisible();
  await expect(page.getByText("APPROVAL", { exact: true })).toBeVisible();
  await expect(page.getByText("PROVIDER", { exact: true })).toBeVisible();

  await page.screenshot({
    path: "../stock_rtx4060_unified/reports/kevpe_event_smoke/dashboard_kevpe_import_badge.png",
    fullPage: true,
  });
});
