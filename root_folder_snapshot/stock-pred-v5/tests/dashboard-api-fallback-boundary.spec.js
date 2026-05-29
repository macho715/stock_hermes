import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test.use({ viewport: { width: 1440, height: 900 } });

const ohlcvRows = Array.from({ length: 80 }, (_, index) => {
  const close = 300 + index * 0.5;
  return {
    date: `2026-03-${String((index % 28) + 1).padStart(2, "0")}`,
    open: close - 0.5,
    high: close + 1.5,
    low: close - 1.5,
    close,
    volume: 1000000 + index * 1000,
  };
});

function modelEvidence(symbol) {
  return {
    schema_version: "model_scores.v1",
    status: "PASS",
    ticker: symbol,
    period: "3y",
    provider: "yfinance",
    model_kind: "logistic",
    model_scores: { main: 58, logistic: 58, xgboost: null, lstm: null, rnn: null },
    ensemble_score: 58,
    signal: "BUY",
    evidence: {
      row_count: 751,
      model_accuracy: 0.53,
      model_auc: 0.56,
      oof_coverage: 0.82,
      generated_at_utc: "2026-05-06T00:00:00+00:00",
    },
  };
}

function snapshotPayload() {
  return {
    schema_version: "dashboard_snapshot.v1",
    generated_at_utc: "2026-05-06T00:00:00+00:00",
    source: "test",
    mode: "report_only",
    disclaimer: "screening_output_only; manual approval required; no broker order execution; not financial advice",
    provider_summary: { status: "PASS", providers_used: ["yfinance"], event_count: 1 },
    config: {
      universe: ["MSFT"],
      track: "BOTH",
      period: "3y",
      top_n: 1,
      synthetic: false,
      data_provider: "yfinance",
      model_kind: "logistic",
    },
    results: [],
  };
}

test("runtime public folder has no synthetic recommendation json or markdown files", async () => {
  const publicDir = path.resolve("public");
  const syntheticRuntimeFiles = fs
    .readdirSync(publicDir)
    .filter((name) => /^recommendations_.*\.(json|md)$/i.test(name));

  expect(syntheticRuntimeFiles).toEqual([]);
});

test("runtime dashboard config controls fallback symbols and REC API defaults", async ({ page }) => {
  const requestedSymbols = [];

  await page.route("**/dashboard_config.json", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        markets: {
          US: {
            fallback_symbols: [
              { symbol: "TEST1", name: "Config Test One" },
              { symbol: "TEST2", name: "Config Test Two" },
            ],
          },
          KRX: { fallback_symbols: [] },
        },
        api_defaults: {
          symbol_period: "1mo",
          model_scores: {
            period: "2y",
            model_kind: "xgboost",
            data_provider: "openbb",
          },
          recommend: {
            track: "S",
            period: "2y",
            top: "3",
            synthetic: "0",
            data_provider: "openbb",
            model_kind: "xgboost",
          },
        },
        signal_thresholds: {
          buy: 61,
          sell: 39,
          label: "BUY >= 61 · HOLD 40-60 · SELL <= 39",
        },
      }),
    });
  });

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: "universe unavailable" }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    const url = new URL(route.request().url());
    requestedSymbols.push({
      symbol: url.searchParams.get("symbol"),
      period: url.searchParams.get("period"),
    });
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "TEST1", source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...modelEvidence(url.searchParams.get("symbol") || "TEST1"),
        model_kind: url.searchParams.get("model_kind"),
        provider: url.searchParams.get("data_provider"),
      }),
    });
  });

  await page.route("**/api/recommend?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(snapshotPayload()),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("UNIVERSE: FALLBACK")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("TEST1", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("BUY >= 61 · HOLD 40-60 · SELL <= 39").first()).toBeVisible();
  await expect.poll(() => requestedSymbols.length).toBeGreaterThan(0);
  expect(requestedSymbols[0]).toEqual({ symbol: "TEST1", period: "1mo" });

  await page.getByRole("button", { name: "REC" }).click();
  const defaults = page.locator("div", { hasText: "API REQUEST DEFAULTS" }).first();
  await expect(defaults).toContainText("track=S");
  await expect(defaults).toContainText("period=2y");
  await expect(defaults).toContainText("top=3");
  await expect(defaults).toContainText("data_provider=openbb");
  await expect(defaults).toContainText("model_kind=xgboost");
});

test("MODELS tab hides optional null LSTM and RNN model rows", async ({ page }) => {
  await page.route("**/dashboard_config.json", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        markets: {
          US: { fallback_symbols: [{ symbol: "MSFT", name: "Microsoft" }] },
          KRX: { fallback_symbols: [] },
        },
        api_defaults: {
          symbol_period: "6mo",
          symbol_data_provider: { US: "yfinance", KRX: "pykrx" },
          model_scores: { period: "3y", model_kind: "auto", data_provider: "yfinance" },
          recommend: {
            track: "BOTH",
            period: "3y",
            top: "5",
            synthetic: "0",
            data_provider: "yfinance",
            model_kind: "auto",
          },
        },
      }),
    });
  });

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [{ symbol: "MSFT", name: "Microsoft" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "MSFT", source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...modelEvidence("MSFT"),
        model_scores: { main: 58, logistic: 58, xgboost: 81.23, lstm: null, rnn: null },
      }),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "MODELS" }).click();

  await expect(page.getByText("XGBoost").first()).toBeVisible();
  await expect(page.getByText("LSTM")).toHaveCount(0);
  await expect(page.getByText("RNN")).toHaveCount(0);
});

test("REC API mode shows request defaults and FILE mode keeps static snapshot boundary", async ({ page }) => {
  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [{ symbol: "MSFT", name: "Microsoft" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "MSFT", source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence("MSFT")),
    });
  });

  await page.route("**/api/recommend?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(snapshotPayload()),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "REC" }).click();

  const defaults = page.locator("div", { hasText: "API REQUEST DEFAULTS" }).first();
  await expect(defaults).toBeVisible({ timeout: 15000 });
  await expect(defaults).toContainText("track=BOTH");
  await expect(defaults).toContainText("period=3y");
  await expect(defaults).toContainText("top=5");
  await expect(defaults).toContainText("synthetic=0");
  await expect(defaults).toContainText("data_provider=yfinance");
  await expect(defaults).toContainText("model_kind=auto");

  await page.getByRole("button", { name: "FILE" }).first().click();

  await expect(page.getByText("STATIC SNAPSHOT")).toBeVisible();
  await expect(page.getByText("API REQUEST DEFAULTS")).toHaveCount(0);
});

test("KRX REC API uses KRX provider defaults and requests the full universe", async ({ page }) => {
  const krxSymbols = [
    "005930.KS",
    "000660.KS",
    "005380.KS",
    "005490.KS",
    "035420.KS",
    "035720.KS",
    "051910.KS",
    "006400.KS",
    "003670.KS",
  ].map((symbol) => ({ symbol, name: symbol }));
  const recommendUrls = [];

  await page.route("**/dashboard_config.json", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        markets: {
          US: { fallback_symbols: [{ symbol: "MSFT", name: "Microsoft" }] },
          KRX: { fallback_symbols: krxSymbols },
        },
        api_defaults: {
          symbol_period: "6mo",
          symbol_data_provider: { US: "yfinance", KRX: "pykrx" },
          model_scores: { period: "3y", model_kind: "auto", data_provider: "yfinance" },
          model_scores_krx: { period: "5y", model_kind: "auto", data_provider: "pykrx" },
          recommend: {
            track: "BOTH",
            period: "3y",
            top: "5",
            synthetic: "0",
            data_provider: "yfinance",
            model_kind: "auto",
          },
          recommend_krx: {
            track: "BOTH",
            period: "5y",
            top: "9",
            synthetic: "0",
            data_provider: "pykrx",
            model_kind: "auto",
          },
        },
      }),
    });
  });

  await page.route("**/api/universe?**", async (route) => {
    const url = new URL(route.request().url());
    const market = url.searchParams.get("market");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market,
        source: "backend_config",
        symbols: market === "KRX" ? krxSymbols : [{ symbol: "MSFT", name: "Microsoft" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ source: "PYKRX", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...modelEvidence(url.searchParams.get("symbol") || "005930.KS"),
        provider: url.searchParams.get("data_provider"),
      }),
    });
  });

  await page.route("**/api/recommend?**", async (route) => {
    recommendUrls.push(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...snapshotPayload(),
        config: {
          ...snapshotPayload().config,
          universe: krxSymbols.map((item) => item.symbol),
          data_provider: "pykrx",
        },
      }),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "KRX" }).click();
  await expect(page.getByText("UNIVERSE: API")).toBeVisible({ timeout: 15000 });

  await page.getByRole("button", { name: "REC" }).click();

  const defaults = page.locator("div", { hasText: "API REQUEST DEFAULTS" }).first();
  await expect(defaults).toContainText("period=5y");
  await expect(defaults).toContainText("top=9");
  await expect(defaults).toContainText("data_provider=pykrx");
  await expect(page.getByRole("button", { name: "FILE" }).first()).toBeEnabled();

  await expect.poll(() => recommendUrls.length).toBeGreaterThan(0);
  const url = new URL(recommendUrls.at(-1));
  expect(url.searchParams.get("data_provider")).toBe("pykrx");
  expect(url.searchParams.get("period")).toBe("5y");
  expect(url.searchParams.get("top")).toBe("9");
  expect(url.searchParams.get("universe")?.split(",")).toHaveLength(9);
});

test("KRX REC keeps LLM advisor enabled and sends blend weight", async ({ page }) => {
  const recommendUrls = [];

  await page.route("**/dashboard_config.json", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        markets: {
          US: { fallback_symbols: [{ symbol: "MSFT", name: "Microsoft" }] },
          KRX: { fallback_symbols: [{ symbol: "005930.KS", name: "Samsung Electronics" }] },
        },
        api_defaults: {
          symbol_period: "6mo",
          symbol_data_provider: { US: "yfinance", KRX: "pykrx" },
          model_scores: { period: "3y", model_kind: "auto", data_provider: "yfinance" },
          model_scores_krx: { period: "5y", model_kind: "auto", data_provider: "pykrx" },
          recommend: {
            track: "BOTH",
            period: "3y",
            top: "5",
            synthetic: "0",
            data_provider: "yfinance",
            model_kind: "auto",
          },
          recommend_krx: {
            period: "3y",
            top: "9",
            data_provider: "pykrx",
          },
        },
      }),
    });
  });

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "KRX",
        source: "backend_config",
        symbols: [{ symbol: "005930.KS", name: "Samsung Electronics" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "005930.KS", source: "PYKRX", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ ...modelEvidence("005930.KS"), provider: "pykrx" }),
    });
  });

  await page.route("**/api/recommend?**", async (route) => {
    recommendUrls.push(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...snapshotPayload(),
        config: {
          ...snapshotPayload().config,
          universe: ["005930.KS"],
          data_provider: "pykrx",
        },
      }),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "KRX" }).click();
  await page.getByRole("button", { name: "REC" }).click();
  const advisorToggle = page.locator("span", { hasText: "LLM ADVISOR" }).locator("xpath=..");
  await expect(advisorToggle).toContainText("OFF");

  await advisorToggle.click();

  await expect(advisorToggle).toContainText("blend_weight=0.30");
  await expect.poll(() => recommendUrls.some((url) => new URL(url).searchParams.get("advisor_blend_weight") === "0.3")).toBe(true);
  const advisorUrl = recommendUrls.find((url) => new URL(url).searchParams.get("advisor_blend_weight") === "0.3");
  expect(new URL(advisorUrl).searchParams.get("data_provider")).toBe("pykrx");
  expect(new URL(advisorUrl).searchParams.get("advisor_run")).toBe("1");
});

test("REC provider card prefers current snapshot provider summary over stale public audit log", async ({ page }) => {
  await page.route("**/dashboard_config.json", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        markets: {
          US: { fallback_symbols: [{ symbol: "MSFT", name: "Microsoft" }] },
          KRX: { fallback_symbols: [{ symbol: "005930.KS", name: "Samsung Electronics" }] },
        },
        api_defaults: {
          symbol_period: "6mo",
          symbol_data_provider: { US: "yfinance", KRX: "pykrx" },
          model_scores: { period: "3y", model_kind: "auto", data_provider: "yfinance" },
          model_scores_krx: { period: "5y", model_kind: "auto", data_provider: "pykrx" },
          recommend: {
            track: "BOTH",
            period: "3y",
            top: "5",
            synthetic: "0",
            data_provider: "yfinance",
            model_kind: "auto",
          },
          recommend_krx: {
            period: "3y",
            top: "9",
            data_provider: "pykrx",
          },
        },
      }),
    });
  });

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "KRX",
        source: "backend_config",
        symbols: [{ symbol: "005930.KS", name: "Samsung Electronics" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ source: "PYKRX", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ ...modelEvidence("005930.KS"), provider: "pykrx" }),
    });
  });

  await page.route("**/api/recommend?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...snapshotPayload(),
        provider_summary: {
          status: "PASS",
          providers_used: ["pykrx"],
          event_count: 9,
          row_count_min: 730,
          last_date_max: "2026-05-29",
        },
        config: {
          ...snapshotPayload().config,
          universe: ["005930.KS"],
          data_provider: "pykrx",
          model_kind: "auto",
        },
      }),
    });
  });

  await page.route("**/audit_log.jsonl", async (route) => {
    await route.fulfill({
      contentType: "text/plain",
      body: JSON.stringify({
        event_type: "provider_attempt",
        provider_used: "synthetic",
        ticker: "OLD.KS",
        status: "SUCCESS",
      }),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "KRX" }).click();
  await page.getByRole("button", { name: "REC" }).click();

  await expect(page.getByText("pykrx · 9 events · rows≥730 · 2026-05-29 · auto")).toBeVisible();
  await expect(page.getByText("synthetic · OLD.KS")).toHaveCount(0);
});

test("REC API dedupes identical in-flight recommendation requests", async ({ page }) => {
  let recommendCalls = 0;
  let releaseRecommend;
  const recommendGate = new Promise((resolve) => {
    releaseRecommend = resolve;
  });

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [{ symbol: "MSFT", name: "Microsoft" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "MSFT", source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence("MSFT")),
    });
  });

  await page.route("**/api/recommend?**", async (route) => {
    recommendCalls += 1;
    await recommendGate;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(snapshotPayload()),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("UNIVERSE: API")).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "REC" }).click();

  await expect.poll(() => recommendCalls, { timeout: 5000 }).toBe(1);
  await page.waitForTimeout(1000);
  expect(recommendCalls).toBe(1);

  releaseRecommend();
  await expect(page.getByText("schema: dashboard_snapshot.v1")).toBeVisible({ timeout: 15000 });
});

test("initial selected ticker waits for backend universe before requesting symbol data", async ({ page }) => {
  const requestedSymbols = [];

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "yfinance",
        symbols: [
          { symbol: "MSFT", name: "Microsoft" },
          { symbol: "NVDA", name: "NVIDIA" },
        ],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    const url = new URL(route.request().url());
    const symbol = url.searchParams.get("symbol");
    requestedSymbols.push(symbol);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol, source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    const url = new URL(route.request().url());
    const symbol = url.searchParams.get("symbol") || "MSFT";
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence(symbol)),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("UNIVERSE: API")).toBeVisible({ timeout: 15000 });
  await expect.poll(() => requestedSymbols.length).toBeGreaterThan(0);
  expect(requestedSymbols[0]).toBe("MSFT");
  expect(requestedSymbols).not.toContain("AAPL");
});

test("REC API waits for backend universe before requesting recommendations", async ({ page }) => {
  const recommendUrls = [];
  let releaseUniverse;
  const universeGate = new Promise((resolve) => {
    releaseUniverse = resolve;
  });

  await page.route("**/api/universe?**", async (route) => {
    await universeGate;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [{ symbol: "MSFT", name: "Microsoft" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "MSFT", source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence("MSFT")),
    });
  });

  await page.route("**/api/recommend?**", async (route) => {
    recommendUrls.push(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(snapshotPayload()),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "REC" }).click();

  await expect(page.getByText("REC API is waiting for `/api/universe`")).toBeVisible();
  expect(recommendUrls).toEqual([]);

  releaseUniverse();

  await expect.poll(() => recommendUrls.length).toBeGreaterThan(0);
  const url = new URL(recommendUrls[0]);
  expect(url.searchParams.get("universe")).toBe("MSFT");
  expect(url.searchParams.get("universe")).not.toContain("AAPL");
});

test("universe API failure uses fallback first symbol and shows fallback state", async ({ page }) => {
  const requestedSymbols = [];

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: "universe unavailable" }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    const url = new URL(route.request().url());
    const symbol = url.searchParams.get("symbol");
    requestedSymbols.push(symbol);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol, source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence(url.searchParams.get("symbol") || "AAPL")),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("UNIVERSE: FALLBACK")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("universe API 503")).toBeVisible();
  await expect.poll(() => requestedSymbols.length).toBeGreaterThan(0);
  expect(requestedSymbols[0]).toBe("AAPL");
});

test("valid explicit ticker selection is not overwritten after backend universe load", async ({ page }) => {
  const requestedSymbols = [];

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [
          { symbol: "MSFT", name: "Microsoft" },
          { symbol: "NVDA", name: "NVIDIA" },
        ],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    const url = new URL(route.request().url());
    const symbol = url.searchParams.get("symbol");
    requestedSymbols.push(symbol);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol, source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence(url.searchParams.get("symbol") || "MSFT")),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("MSFT", { exact: true }).first()).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: /NVDA/ }).click();
  await expect(page.getByText("NVDA", { exact: true }).first()).toBeVisible();
  await page.waitForTimeout(500);

  expect(requestedSymbols).toContain("NVDA");
  expect(requestedSymbols.at(-1)).toBe("NVDA");
});

test("symbol API failure shows unavailable state without synthetic chart fallback", async ({ page }) => {
  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [{ symbol: "MSFT", name: "Microsoft" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "MSFT", source: "YFINANCE", data: [] }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence("MSFT")),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("REAL DATA LOAD FAILED")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("MSFT chart data was not rendered")).toBeVisible();
  await expect(page.getByText("backend API returned insufficient OHLCV rows")).toBeVisible();
  await expect(page.getByText("SOURCE YFINANCE")).toHaveCount(0);
});

test("initial AAPL chart recovers from a transient symbol API failure", async ({ page }) => {
  let symbolRequests = 0;

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [{ symbol: "AAPL", name: "Apple Inc." }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    symbolRequests += 1;
    if (symbolRequests === 1) {
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ error: "backend API 502" }),
      });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol: "AAPL", source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence("AAPL")),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("REAL DATA LOAD FAILED")).toHaveCount(0, { timeout: 15000 });
  await expect(page.getByText("SRC")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("YFINANCE", { exact: true })).toBeVisible({ timeout: 15000 });
  expect(symbolRequests).toBeGreaterThanOrEqual(2);
});

test("initial AAPL chart does not stay loading when sidebar prefetch fills cache first", async ({ page }) => {
  let symbolRequests = 0;

  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "US",
        source: "backend_config",
        symbols: [
          { symbol: "AAPL", name: "Apple Inc." },
          { symbol: "MSFT", name: "Microsoft" },
        ],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    const url = new URL(route.request().url());
    const symbol = url.searchParams.get("symbol") || "AAPL";
    if (symbol === "AAPL") {
      symbolRequests += 1;
      if (symbolRequests === 1) {
        await new Promise((resolve) => setTimeout(resolve, 900));
      }
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ symbol, source: "YFINANCE", data: ohlcvRows }),
    });
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence("AAPL")),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });

  await expect(page.getByText("REAL DATA LOAD FAILED")).toHaveCount(0, { timeout: 15000 });
  await expect(page.getByText("FETCHING AAPL")).toHaveCount(0, { timeout: 15000 });
  await expect(page.getByText("SRC")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("YFINANCE", { exact: true })).toBeVisible({ timeout: 15000 });
  expect(symbolRequests).toBeGreaterThanOrEqual(2);
});

test("symbol API network failure is shown as backend unreachable instead of insufficient rows", async ({ page }) => {
  await page.route("**/api/universe?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        market: "KRX",
        source: "backend_config",
        symbols: [{ symbol: "005930.KS", name: "Samsung Electronics" }],
      }),
    });
  });

  await page.route("**/api/symbol?**", async (route) => {
    await route.abort("failed");
  });

  await page.route("**/api/model-scores?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(modelEvidence("005930.KS")),
    });
  });

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "KRX" }).click();

  await expect(page.getByText("REAL DATA LOAD FAILED")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("005930.KS chart data was not rendered because the backend API could not be reached.")).toBeVisible();
  await expect(page.getByText("backend/provider did not return enough OHLCV rows")).toHaveCount(0);
});
