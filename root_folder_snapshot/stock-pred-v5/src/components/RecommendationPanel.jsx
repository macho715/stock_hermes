import React, { useState, useEffect, useCallback, useRef } from "react";
import RecommendationCard from "./RecommendationCard";

const C = {
  bg: "#050A0E",
  bgDeep: "#02060A",
  panel: "#0A1218",
  panel2: "#0E1822",
  panelHi: "#13202C",
  border: "#1A2A38",
  borderHi: "#243648",
  text: "#D4E1EC",
  textDim: "#6B7E8E",
  textMuted: "#3F5060",
  green: "#00FF88",
  red: "#FF3366",
  amber: "#FFB800",
  us: "#00CCFF",
  krx: "#FF6B35",
};

const FONT = '"JetBrains Mono","Fira Code",ui-monospace,SFMono-Regular,Menlo,monospace';

async function fetchDashboardSnapshot(jsonPath) {
  try {
    const res = await fetch(jsonPath);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function fetchOptionalText(path) {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.text();
  } catch (e) {
    return null;
  }
}

function parseAuditLog(text) {
  if (!text) {
    return { available: false, eventCount: 0, providerEvents: 0, successEvents: 0, latestProvider: "—", latestStatus: "—" };
  }
  const events = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try { return JSON.parse(line); } catch (e) { return null; }
    })
    .filter(Boolean);
  const providerEvents = events.filter((e) => e.event_type === "provider_attempt");
  const latest = providerEvents[providerEvents.length - 1] || events[events.length - 1] || {};
  return {
    available: events.length > 0,
    eventCount: events.length,
    providerEvents: providerEvents.length,
    successEvents: events.filter((e) => e.status === "SUCCESS").length,
    latestProvider: latest.provider_used || latest.provider_requested || "—",
    latestStatus: latest.status || "—",
    latestTicker: latest.ticker || "—",
  };
}

function parseCsvRows(text) {
  if (!text) return [];
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    return headers.reduce((row, header, index) => {
      row[header] = (values[index] || "").trim();
      return row;
    }, {});
  });
}

function summarizeApproval(text, snapshot) {
  const rows = parseCsvRows(text);
  const snapshotNeedsApproval = snapshot?.disclaimer?.toLowerCase().includes("manual approval")
    || snapshot?.results?.some((r) => r.screening_output_only === true);
  return {
    available: rows.length > 0,
    rowCount: rows.length,
    pendingCount: rows.filter((r) => r.manual_action === "REVIEW_PENDING" || r.manual_approval_required === "True").length,
    brokerBlocked: rows.length > 0
      ? rows.every((r) => String(r.broker_order_execution).toLowerCase() === "false")
      : true,
    status: snapshotNeedsApproval ? "MANUAL REVIEW" : "NO REVIEW FLAG",
  };
}

function validateDashboardSnapshot(data) {
  if (!data || typeof data !== "object") {
    throw new Error("dashboard_snapshot JSON object is required");
  }
  if (data.schema_version !== "dashboard_snapshot.v1") {
    throw new Error("schema_version must be dashboard_snapshot.v1");
  }
  if (!Array.isArray(data.results)) {
    throw new Error("results array is required");
  }
  return data;
}

export default function RecommendationPanel({ jsonPath, apiUrl, currency = "$", accent = "#00CCFF" }) {
  const importInputRef = useRef(null);
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [importedFileName, setImportedFileName] = useState("");
  const [auditSummary, setAuditSummary] = useState(null);
  const [approvalSummary, setApprovalSummary] = useState(null);
  const [tab, setTab] = useState("ALL");
  const [sortBy, setSortBy] = useState("score");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    let data = null;

    // Option A: file-based JSON fetch
    if (jsonPath) {
      data = await fetchDashboardSnapshot(jsonPath);
    }
    // Option B: HTTP API fetch
    else if (apiUrl) {
      try {
        const res = await fetch(apiUrl);
        if (!res.ok) throw new Error(`API ${res.status}`);
        data = await res.json();
      } catch (e) {
        setError(`API error: ${e.message}`);
        setLoading(false);
        return;
      }
    }

    if (!data) {
      setError("No data source configured. Set jsonPath or apiUrl prop.");
      setLoading(false);
      return;
    }

    setSnapshot(data);
    setImportedFileName("");
    setLoading(false);
  }, [jsonPath, apiUrl]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let cancelled = false;
    async function loadOperationalFiles() {
      if (!snapshot) return;
      const [auditText, approvalText] = await Promise.all([
        fetchOptionalText("/audit_log.jsonl"),
        fetchOptionalText("/approval_journal_template.csv"),
      ]);
      if (cancelled) return;
      setAuditSummary(parseAuditLog(auditText));
      setApprovalSummary(summarizeApproval(approvalText, snapshot));
    }
    loadOperationalFiles();
    return () => { cancelled = true; };
  }, [snapshot]);

  const handleImportFile = useCallback((event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = validateDashboardSnapshot(JSON.parse(String(reader.result || "")));
        setSnapshot(data);
        setImportedFileName(file.name);
        setError(null);
      } catch (e) {
        setError(`Import error: ${e.message}`);
      } finally {
        event.target.value = "";
      }
    };
    reader.onerror = () => {
      setError("Import error: file read failed");
      event.target.value = "";
    };
    reader.readAsText(file);
  }, []);

  const filtered = snapshot?.results
    ? snapshot.results.filter((r) => {
        if (tab === "ALL") return true;
        if (tab === "GREEN") return r.verdict?.includes("ELIGIBLE") || r.verdict?.includes("ACCUMULATE");
        if (tab === "AMBER") return r.verdict?.includes("AMBER");
        if (tab === "RED") return r.verdict?.startsWith("RED") || r.verdict?.startsWith("ZERO");
        return true;
      }).sort((a, b) => {
        if (sortBy === "score") return (b.score || 0) - (a.score || 0);
        if (sortBy === "rr") return (b.risk_reward || 0) - (a.risk_reward || 0);
        return 0;
      })
    : [];

  const verdictCounts = snapshot?.results
    ? {
        GREEN: snapshot.results.filter(r => r.verdict?.includes("ELIGIBLE") || r.verdict?.includes("ACCUMULATE")).length,
        AMBER: snapshot.results.filter(r => r.verdict?.includes("AMBER")).length,
        RED: snapshot.results.filter(r => r.verdict?.startsWith("RED") || r.verdict?.startsWith("ZERO")).length,
      }
    : { GREEN: 0, AMBER: 0, RED: 0 };

  const providerSummary = snapshot
    ? {
        provider: auditSummary?.latestProvider && auditSummary.latestProvider !== "—"
          ? auditSummary.latestProvider
          : (snapshot.config?.data_provider || snapshot.source || "—"),
        status: auditSummary?.latestStatus || (snapshot.result_count > 0 ? "SNAPSHOT_READY" : "NO_RESULTS"),
        ticker: auditSummary?.latestTicker || snapshot.config?.universe?.[0] || "—",
        model: snapshot.config?.model_kind || "—",
        device: snapshot.config?.xgb_device || "—",
      }
    : null;

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200, color: C.textDim, fontSize: 11, letterSpacing: 2 }}>
        ◌ LOADING RECOMMENDATIONS...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 16, color: C.red, fontSize: 10, fontFamily: FONT }}>
        ⚠ {error}
        <button onClick={load} style={{ display: "block", marginTop: 8, padding: "4px 8px", background: "transparent", border: `1px solid ${C.border}`, color: C.textDim, cursor: "pointer", fontFamily: FONT, fontSize: 9 }}>
          ↻ RETRY
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Source controls */}
      <div style={{
        padding: "8px 10px",
        background: C.bgDeep,
        borderBottom: `1px solid ${C.border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
        fontFamily: FONT,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <button
            onClick={load}
            style={{
              background: importedFileName ? "transparent" : `${accent}18`,
              border: `1px solid ${importedFileName ? C.borderHi : accent}`,
              color: importedFileName ? C.textDim : accent,
              fontFamily: FONT,
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: 1,
              padding: "5px 9px",
              cursor: "pointer",
            }}
          >
            FILE
          </button>
          <button
            onClick={() => importInputRef.current?.click()}
            style={{
              background: importedFileName ? `${C.green}18` : "transparent",
              border: `1px solid ${importedFileName ? C.green : C.borderHi}`,
              color: importedFileName ? C.green : C.textDim,
              fontFamily: FONT,
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: 1,
              padding: "5px 9px",
              cursor: "pointer",
            }}
          >
            IMPORT
          </button>
          <input
            ref={importInputRef}
            aria-label="Import dashboard snapshot JSON"
            type="file"
            accept=".json,application/json"
            onChange={handleImportFile}
            style={{ display: "none" }}
          />
        </div>
        <div style={{
          minWidth: 0,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: importedFileName ? C.green : C.textMuted,
          fontSize: 8,
          letterSpacing: 1,
        }}>
          {importedFileName ? `IMPORTED · ${importedFileName}` : (jsonPath ? `FIXED FILE · ${jsonPath}` : `API · ${apiUrl || "—"}`)}
        </div>
      </div>

      {/* Source info */}
      {snapshot && (
        <div style={{
          padding: "6px 10px",
          background: C.bgDeep,
          borderBottom: `1px solid ${C.border}`,
          fontSize: 8,
          color: C.textMuted,
          fontFamily: FONT,
          letterSpacing: 1,
          display: "flex",
          justifyContent: "space-between",
        }}>
          <span>ALGO v2 · {snapshot.config?.universe || "—"} · Track-{snapshot.config?.track || "BOTH"}</span>
          <span>{new Date(snapshot.generated_at_utc || Date.now()).toLocaleString()}</span>
        </div>
      )}

      {/* Operational summary */}
      {snapshot && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 6,
          padding: "8px 10px",
          background: C.panel,
          borderBottom: `1px solid ${C.border}`,
          fontFamily: FONT,
        }}>
          {[
            {
              title: "AUDIT",
              status: auditSummary?.available ? `${auditSummary.eventCount} EVENTS` : "NO PUBLIC LOG",
              detail: auditSummary?.available
                ? `${auditSummary.providerEvents} provider · ${auditSummary.successEvents} success`
                : (snapshot.audit_log_path || "audit_log.jsonl missing"),
              color: auditSummary?.available ? C.green : C.amber,
            },
            {
              title: "APPROVAL",
              status: approvalSummary?.available ? `${approvalSummary.pendingCount} PENDING` : approvalSummary?.status || "MANUAL REVIEW",
              detail: approvalSummary?.available
                ? `${approvalSummary.rowCount} rows · broker ${approvalSummary.brokerBlocked ? "blocked" : "check"}`
                : "screening only · manual approval required",
              color: approvalSummary?.pendingCount > 0 ? C.amber : C.green,
            },
            {
              title: "PROVIDER",
              status: providerSummary?.status || "—",
              detail: `${providerSummary?.provider || "—"} · ${providerSummary?.ticker || "—"} · ${providerSummary?.model || "—"} · ${providerSummary?.device || "—"}`,
              color: providerSummary?.status === "SUCCESS" || providerSummary?.status === "SNAPSHOT_READY" ? C.green : C.amber,
            },
          ].map((item) => (
            <div key={item.title} style={{
              minWidth: 0,
              padding: "7px 8px",
              background: C.bgDeep,
              border: `1px solid ${C.borderHi}`,
              borderLeft: `3px solid ${item.color}`,
            }}>
              <div style={{ fontSize: 8, color: C.textMuted, letterSpacing: 1.5, marginBottom: 3 }}>
                {item.title}
              </div>
              <div style={{
                color: item.color,
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 1,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}>
                {item.status}
              </div>
              <div style={{
                marginTop: 2,
                color: C.textDim,
                fontSize: 8,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}>
                {item.detail}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filter tabs */}
      <div style={{ display: "flex", borderBottom: `1px solid ${C.border}`, background: C.bgDeep }}>
        {[
          { key: "ALL", label: `ALL (${snapshot?.result_count || 0})`, color: C.textDim },
          { key: "GREEN", label: `GREEN (${verdictCounts.GREEN})`, color: C.green },
          { key: "AMBER", label: `AMBER (${verdictCounts.AMBER})`, color: C.amber },
          { key: "RED", label: `RED (${verdictCounts.RED})`, color: C.red },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1, padding: "7px 0",
              background: tab === t.key ? C.panelHi : "transparent",
              border: "none",
              borderBottom: `2px solid ${tab === t.key ? t.color : "transparent"}`,
              color: tab === t.key ? t.color : C.textMuted,
              fontFamily: FONT, fontWeight: 600, letterSpacing: 1.5, fontSize: 9,
              cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Sort */}
      <div style={{ padding: "4px 10px", display: "flex", justifyContent: "flex-end", gap: 8, borderBottom: `1px solid ${C.border}`, background: C.panel }}>
        <span style={{ fontSize: 8, color: C.textMuted, letterSpacing: 1 }}>SORT:</span>
        {[{ k: "score", l: "SCORE" }, { k: "rr", l: "R/R" }].map(s => (
          <button
            key={s.k}
            onClick={() => setSortBy(s.k)}
            style={{
              background: "transparent", border: "none",
              color: sortBy === s.k ? accent : C.textMuted,
              fontFamily: FONT, fontSize: 8, letterSpacing: 1,
              cursor: "pointer",
            }}
          >
            {s.l}
          </button>
        ))}
      </div>

      {/* Cards */}
      <div style={{ padding: 8, overflowY: "auto", maxHeight: "calc(100vh - 300px)" }}>
        {filtered.length === 0 ? (
          <div style={{ color: C.textDim, fontSize: 10, textAlign: "center", padding: 24 }}>
            No recommendations match this filter
          </div>
        ) : (
          filtered.map((r, index) => (
            <RecommendationCard
              key={`${r.ticker || "candidate"}-${r.track || r.verdict || "row"}-${index}`}
              result={r}
              currency={currency}
              accent={accent}
            />
          ))
        )}
      </div>

      {/* Footer */}
      {snapshot && (
        <div style={{
          padding: "6px 10px",
          borderTop: `1px solid ${C.border}`,
          fontSize: 8,
          color: C.textMuted,
          fontFamily: FONT,
          lineHeight: 1.5,
        }}>
          <div style={{ color: C.amber, marginBottom: 2 }}>⚠ {snapshot.disclaimer?.slice(0, 80) || "screening_output_only — manual approval required"}</div>
          <div>schema: {snapshot.schema_version} · source: {snapshot.source}</div>
        </div>
      )}
    </div>
  );
}
