import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const snapshotPath = path.join(root, "reports", "dashboard_bridge_smoke", "dashboard_snapshot.json");
const outDir = path.join(root, "reports", "dashboard_browser_verification");
const fixturePath = path.join(outDir, "snapshot_fixture.js");
const screenshotPath = path.join(outDir, "backend_snapshot_smoke.png");
const reportPath = path.join(outDir, "dashboard_browser_verification.md");
const htmlPath = path.join(__dirname, "bridge_smoke.html");

fs.mkdirSync(outDir, { recursive: true });
const snapshotText = fs.readFileSync(snapshotPath, "utf8");
const snapshot = JSON.parse(snapshotText);
fs.writeFileSync(fixturePath, `window.DASHBOARD_SNAPSHOT = ${snapshotText};\n`, "utf8");

const url = `file:///${htmlPath.replaceAll("\\", "/")}`;
const result = spawnSync(
  "npx",
  [
    "playwright",
    "screenshot",
    "--channel=chrome",
    "--viewport-size=1366,900",
    "--wait-for-selector",
    "body[data-status=\"loaded\"]",
    "--full-page",
    url,
    screenshotPath,
  ],
  { stdio: "inherit", shell: process.platform === "win32" }
);

if ((result.status ?? 1) !== 0) {
  process.exit(result.status ?? 1);
}

const lines = [
  "# Dashboard Browser Verification",
  "",
  "| Item | Value |",
  "|---|---|",
  "| Status | SNAPSHOT LOADED |",
  `| Schema | ${snapshot.schema_version} |`,
  `| Mode | ${snapshot.mode} |`,
  `| Result count | ${snapshot.result_count ?? snapshot.results?.length ?? 0} |`,
  `| First ticker | ${snapshot.results?.[0]?.ticker ?? ""} |`,
  `| Audit path | ${snapshot.audit_log_path ?? ""} |`,
  `| Screenshot | ${path.relative(root, screenshotPath)} |`,
  `| Fixture | ${path.relative(root, fixturePath)} |`,
  "",
  "Result: PASS. Playwright CLI opened the local browser harness and captured the rendered backend snapshot evidence.",
  "",
];

fs.writeFileSync(reportPath, lines.join("\n"), "utf8");
console.log(JSON.stringify({ result: "PASS", reportPath, screenshotPath, fixturePath }, null, 2));
