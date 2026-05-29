Use `$design-upgrade-loop` at `C:\Users\jichu\.codex\skills\design-upgrade-loop\SKILL.md` as the governing P0-P7 workflow for this run. Reuse its source routing, patch-map discipline, artifact contract, and verification thresholds. Do not continue if that skill cannot be read or followed.
Run this work as the P0-P7 design pipeline.

P0 Intake
- editable targets:
- `root_folder_snapshot\stock-pred-v5\src\StockPredV5.jsx`
- `root_folder_snapshot\stock-pred-v5\src\components\RecommendationCard.jsx`
- evidence: use the latest screenshot or preview at `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950\before.png` as the baseline
- constraints: Respect these constraints: Operational investment dashboard; keep dense scan-first workflow; no marketing hero; preserve safety badges and report-only investment constraints; desktop first with readable compact panels.

P1 Baseline and P2 Benchmark
- assign to `reference_hunter`
- run the actual web search runner command first: `python "C:\Users\jichu\.codex\skills\design-upgrade-loop\scripts\run_web_benchmark_search.py" --profile dashboard --target "root_folder_snapshot\stock-pred-v5\src\StockPredV5.jsx" --output "C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/search-log.json"`
- save the real search log to `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/search-log.json`
- run the search-log validator command: `python "C:\Users\jichu\.codex\skills\design-upgrade-loop\scripts\validate_search_log.py" "C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/search-log.json"`
- perform live web search for current well-known dashboard references for dense operational UIs and extract at least 3 transferable elements across at least 2 source families
- save the human-readable benchmark log to `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/refs.md`
- save the structured benchmark artifact to `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/design-benchmark.json`
- run the benchmark validator command: `python "C:\Users\jichu\.codex\skills\design-upgrade-loop\scripts\validate_design_benchmark.py" "C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/design-benchmark.json"`
- run the benchmark gate command: `python "C:\Users\jichu\.codex\skills\design-upgrade-loop\scripts\validate_benchmark_gate.py" "C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/search-log.json" "C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/design-benchmark.json" --output "C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/benchmark-gate.json"`
- return baseline issues, reference log, transferable elements, candidate patch targets, and anti-patterns
- treat live web benchmark search as mandatory
- if the search runner fails, if the search-log validator fails, if live web search fails, if fewer than 3 current well-known references are returned, if the output relies on memory-only recommendations, if the benchmark validator fails, or if the benchmark gate validator fails, stop and report NOT DONE

P3 Patch Map and P4 Apply
- assign to `design_patcher`
- require the validated benchmark artifact at `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/design-benchmark.json` before allowing `P3`
- require the validated benchmark gate artifact at `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/benchmark-gate.json` before allowing `P3`
- do not allow a normal PASS path when the benchmark evidence is `site_probe`-only
- improve KPI hierarchy, filter ergonomics, table density, status clarity, and executive readability with the smallest defensible patch set across:
- `root_folder_snapshot\stock-pred-v5\src\StockPredV5.jsx`
- `root_folder_snapshot\stock-pred-v5\src\components\RecommendationCard.jsx`
- require an exact patch map before wide-impact edits

P5 Verify and P6 Iterate
- assign to `visual_verifier`
- inspect the result with focus on hierarchy, spacing, information clarity, and usability
- save artifacts under `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/`, write `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\design-upgrade\20260530_020950/design-scorecard.json`, run the validator if available, and report PASS or FAIL with the weakest metric
- if FAIL, identify the smallest next improvement

P7 Deliver
- summarize:
  - references used
  - transferable design elements
  - files changed
  - exact patch points
  - scorecard result
  - remaining risks
