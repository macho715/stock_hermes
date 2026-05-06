import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1440, height: 900 } });

const ohlcvRows = Array.from({ length: 80 }, (_, index) => {
  const close = 180 + index * 0.35;
  return {
    date: `2026-02-${String((index % 28) + 1).padStart(2, "0")}`,
    open: close - 0.4,
    high: close + 1.2,
    low: close - 1.1,
    close,
    volume: 1000000 + index * 1000,
  };
});

const weakModelEvidence = {
  schema_version: "model_scores.v1",
  status: "PASS",
  ticker: "AAPL",
  period: "3y",
  provider: "yfinance",
  model_kind: "logistic",
  model_scores: {
    logistic: 67.3,
    xgboost: 63.2,
    lstm: 59.4,
    rnn: null,
    main: 67.3,
  },
  ensemble_score: 67.3,
  signal: "BUY",
  evidence: {
    row_count: 751,
    feature_rows: 493,
    model_accuracy: 0.457995,
    model_auc: 0.469873,
    oof_coverage: 0.748479,
    generated_at_utc: "2026-05-05T05:27:25+00:00",
  },
};

async function mockBackend(page) {
  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ market: "US", symbols: [{ symbol: "AAPL", name: "Apple Inc." }] }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "AAPL", source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(weakModelEvidence),
    });
  });
}

test("shows weak model quality warning and backend thresholds in SIGNAL and MODELS", async ({ page }) => {
  await mockBackend(page);

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("BACKEND MODEL EVIDENCE", { exact: true })).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("모델 품질 낮음: 검토 전용")).toBeVisible();
  await expect(page.getByText("BUY >= 56 · HOLD 45-55 · SELL <= 44").first()).toBeVisible();
  await expect(page.getByText("BUY ≥ 65 · HOLD 36-64 · SELL ≤ 35")).toHaveCount(0);

  await page.getByRole("button", { name: "MODELS" }).click();

  await expect(page.getByText("BACKEND MODEL COMPARISON")).toBeVisible();
  await expect(page.getByText("모델 품질 낮음: 검토 전용")).toBeVisible();
  await expect(page.getByText("63.2")).toBeVisible();
  await expect(page.getByText("59.4")).toBeVisible();
  await expect(page.getByText("Shows N/A unless the backend selected XGBoost for this ticker")).toHaveCount(0);
  await expect(page.getByText("Not active in Phase 1; TensorFlow/LSTM is optional backend evidence")).toHaveCount(0);
  await expect(page.getByText("AUC")).toBeVisible();
  await expect(page.getByText("0.470")).toBeVisible();
});
