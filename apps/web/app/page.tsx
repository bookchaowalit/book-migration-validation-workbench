"use client";

import { useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8765";

type Dataset = {
  filename: string;
  contentBase64: string;
  fields: string[];
  format: string;
};

type Suggestion = {
  source: string;
  target: string | null;
  confidence: number;
  method: string;
  auto_selected: boolean;
};

type ReviewStatus = "unreviewed" | "approved" | "rejected" | "needs-review";

type Evidence = {
  evidence_id: string;
  status: string;
  status_label: string;
  key: string;
  reason: string;
  legacy: Record<string, string> | null;
  target: Record<string, string> | null;
  mismatches: Array<{
    legacy_field: string;
    target_field: string;
    legacy_value: string;
    target_value: string;
  }>;
  match_candidates: Array<{
    target_key?: string;
    candidate_key?: string;
    score: number;
    threshold: number;
    auto_approved: boolean;
    reason: string;
    field_scores: Array<{
      source_field?: string;
      candidate_field?: string;
      legacy_field?: string;
      target_field?: string;
      score: number;
    }>;
    row_number: number;
  }>;
  review_status: ReviewStatus;
};

type AuditPackage = {
  schema_version: string;
  rule_version: string;
  fingerprints: {
    legacy_input_sha256?: string;
    target_input_sha256?: string;
    configuration_sha256?: string;
    audit_package_sha256?: string;
  };
};

type Result = {
  summary: {
    records_checked: number;
    matched: number;
    exceptions: number;
    match_rate: number;
    counts: Record<string, number>;
  };
  mapping_suggestions: Suggestion[];
  applied_mapping: Record<string, string>;
  evidence: Evidence[];
  sql: string;
  input: { legacy: { sha256: string }; target: { sha256: string } };
  configuration_fingerprint: string;
  normalization?: {
    name: string;
    label: string;
    description: string;
    field_rules: string[];
    raw_evidence_preserved: boolean;
  };
  fuzzy_matching?: {
    enabled: boolean;
    candidate_minimum: number;
    review_threshold: number;
    candidate_limit: number;
    auto_approval: boolean;
  };
  review_summary?: Record<ReviewStatus, number>;
  redacted_export?: Result;
  audit_package?: AuditPackage;
  engine?: { legacy: Record<string, unknown>; target: Record<string, unknown> };
};

type ApiError = { error?: string };

async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  return btoa(binary);
}

async function readApi<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = (await response.json()) as T & ApiError;
  if (!response.ok) throw new Error(data.error || "API request failed");
  return data;
}

function firstValue(row: Record<string, string> | null): string {
  return row ? Object.values(row)[0] || "—" : "—";
}

function reviewLabel(status: ReviewStatus): string {
  return {
    unreviewed: "ยังไม่ review",
    approved: "อนุมัติ",
    rejected: "ไม่อนุมัติ",
    "needs-review": "ต้องตรวจเพิ่ม",
  }[status];
}

function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export default function WorkbenchPage() {
  const [legacy, setLegacy] = useState<Dataset | null>(null);
  const [target, setTarget] = useState<Dataset | null>(null);
  const [legacyKey, setLegacyKey] = useState("");
  const [targetKey, setTargetKey] = useState("");
  const [legacyTable, setLegacyTable] = useState("legacy_customers");
  const [targetTable, setTargetTable] = useState("new_customers");
  const [normalizationProfile, setNormalizationProfile] = useState("generic");
  const [fuzzyEnabled, setFuzzyEnabled] = useState(true);
  const [fuzzyThreshold, setFuzzyThreshold] = useState("0.90");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [reviewStatuses, setReviewStatuses] = useState<Record<string, ReviewStatus>>({});
  const [result, setResult] = useState<Result | null>(null);
  const [selected, setSelected] = useState<Evidence | null>(null);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const suggestions = result?.mapping_suggestions || [];
  const filteredEvidence = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return (result?.evidence || []).filter((item) => (
      (filter === "all" || item.status === filter)
      && (!normalized || item.key.toLowerCase().includes(normalized))
    ));
  }, [filter, query, result]);

  function chooseDefault(fields: string[]): string {
    return fields.find((field) => field === "account_no")
      || fields.find((field) => field === "id")
      || fields[0]
      || "";
  }

  async function inspect(side: "legacy" | "target", file: File) {
    setError("");
    try {
      const contentBase64 = await fileToBase64(file);
      const data = await readApi<{ input: { fields: string[]; format: string } }>("/api/inspect", {
        filename: file.name,
        content_base64: contentBase64,
      });
      const dataset = { filename: file.name, contentBase64, fields: data.input.fields, format: data.input.format };
      if (side === "legacy") {
        setLegacy(dataset);
        setLegacyKey(chooseDefault(dataset.fields));
      } else {
        setTarget(dataset);
        setTargetKey(chooseDefault(dataset.fields));
      }
      setResult(null);
      setSelected(null);
      setMapping({});
      setReviewStatuses({});
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "อ่านไฟล์ไม่สำเร็จ");
    }
  }

  async function loadSample() {
    setBusy(true);
    setError("");
    try {
      const files = await Promise.all([
        fetch(`${API_BASE_URL}/fixtures/legacy_customers.csv`),
        fetch(`${API_BASE_URL}/fixtures/new_customers.csv`),
      ]);
      if (files.some((response) => !response.ok)) throw new Error("โหลดข้อมูลตัวอย่างไม่สำเร็จ");
      const [legacyBlob, targetBlob] = await Promise.all(files.map((response) => response.blob()));
      await inspect("legacy", new File([legacyBlob], "legacy_customers.csv", { type: "text/csv" }));
      await inspect("target", new File([targetBlob], "new_customers.csv", { type: "text/csv" }));
      await new Promise((resolve) => setTimeout(resolve, 0));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "โหลดข้อมูลตัวอย่างไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function reconcile() {
    if (!legacy || !target || !legacyKey || !targetKey) return;
    setBusy(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        legacy_file_base64: legacy.contentBase64,
        legacy_filename: legacy.filename,
        target_file_base64: target.contentBase64,
        target_filename: target.filename,
        legacy_key: legacyKey,
        target_key: targetKey,
        legacy_table: legacyTable,
        target_table: targetTable,
        normalization_profile: normalizationProfile,
        fuzzy_enabled: fuzzyEnabled,
        fuzzy_threshold: Number(fuzzyThreshold),
      };
      if (result) payload.mapping = { ...mapping, [legacyKey]: targetKey };
      if (result) payload.review_statuses = reviewStatuses;
      const next = await readApi<Result>("/api/reconcile", payload);
      setResult(next);
      setMapping(next.applied_mapping);
      setReviewStatuses(Object.fromEntries(next.evidence.map((item) => [item.evidence_id, item.review_status])));
      setSelected(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Reconciliation ไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  function toggleMapping(source: string, checked: boolean, suggestedTarget: string | null) {
    setMapping((current) => {
      const next = { ...current };
      if (checked && suggestedTarget) next[source] = suggestedTarget;
      else delete next[source];
      return next;
    });
  }

  function setReviewStatus(evidenceId: string, status: ReviewStatus) {
    setReviewStatuses((current) => ({ ...current, [evidenceId]: status }));
  }

  function makeReport() {
    if (!result) return "";
    const lines = [
      "# Migration Validation Report",
      "",
      `- Generated: ${new Date().toISOString()}`,
      `- Legacy file: ${legacy?.filename || "uploaded file"}`,
      `- Target file: ${target?.filename || "uploaded file"}`,
      `- Records checked: ${result.summary.records_checked}`,
      `- Match rate: ${result.summary.match_rate}%`,
      `- Exceptions: ${result.summary.exceptions}`,
      `- Configuration fingerprint: ${result.configuration_fingerprint}`,
      `- Audit package fingerprint: ${result.audit_package?.fingerprints.audit_package_sha256 || "not available"}`,
      `- Normalization profile: ${result.normalization?.name || normalizationProfile}`,
      `- Fuzzy review: ${result.fuzzy_matching?.enabled ? `enabled at ${Math.round((result.fuzzy_matching.review_threshold || Number(fuzzyThreshold)) * 100)}%` : "disabled"} · auto-approval: false`,
      "- Export mode: field-profile redacted",
      "",
      "## Status counts",
      "",
      ...Object.entries(result.summary.counts).map(([status, count]) => `- ${status}: ${count}`),
      "",
      "## Review status",
      "",
      ...result.evidence.map((item) => `- ${item.key}: ${reviewLabel(reviewStatuses[item.evidence_id] || item.review_status)}`),
      "",
      "## Applied mapping",
      "",
      ...Object.entries(result.applied_mapping).map(([source, destination]) => `- \`${source}\` → \`${destination}\``),
    ];
    return lines.join("\n");
  }

  const canRun = Boolean(legacy && target && legacyKey && targetKey);
  const statusOptions = result
    ? Object.entries(result.summary.counts).filter(([, count]) => count > 0)
    : [];

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="eyebrow">TRACE / V1.0</span>
          <h1>Migration Validation Workbench</h1>
          <p>ตรวจข้อมูลหลัง migration ให้เห็นหลักฐานทุกแถว ก่อนปล่อยระบบใหม่</p>
        </div>
        <div className="top-actions">
          <span className="status-pill"><span className="status-dot" />LOCAL ONLY</span>
          <button className="button ghost" onClick={loadSample} disabled={busy}>ใช้ข้อมูลตัวอย่าง</button>
        </div>
      </header>

      <section className="hero-grid">
        <div className="hero-copy">
          <span className="section-kicker">MIGRATION CONTROL ROOM</span>
          <h2>จาก “น่าจะย้ายครบ”<br /><em>เป็นหลักฐานที่ตรวจซ้ำได้</em></h2>
          <p>ใส่ข้อมูลจากระบบเก่าและระบบใหม่ เลือก key แล้วให้ workbench แยก match, mismatch, missing และ duplicate ให้ทันที</p>
        </div>
        <div className="hero-note">
          <span className="note-label">CURRENT RUN</span>
          <strong>{result ? `${result.summary.records_checked.toLocaleString()} records` : "ยังไม่มีการตรวจ"}</strong>
          <span className="muted">ไฟล์จะถูกประมวลผลในหน่วยความจำและไม่ถูกบันทึกลงดิสก์</span>
        </div>
      </section>

      <section className="panel setup-panel">
        <div className="panel-heading"><div><span className="section-kicker">01 / INPUTS</span><h3>เลือกข้อมูลสองฝั่ง</h3></div><span className="step-label">SOURCE → TARGET</span></div>
        <div className="input-grid">
          <label className="upload-card" htmlFor="legacy-file"><span className="card-index">A</span><span className="upload-title">ระบบเก่า / Legacy</span><span className="file-name">{legacy ? `${legacy.filename} · ${legacy.fields.length} fields · ${legacy.format}` : "เลือกไฟล์ CSV / XLSX / Parquet"}</span><input id="legacy-file" type="file" accept=".csv,.xlsx,.parquet,.tsv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void inspect("legacy", file); }} /></label>
          <div className="flow-arrow" aria-hidden="true">→</div>
          <label className="upload-card target" htmlFor="target-file"><span className="card-index">B</span><span className="upload-title">ระบบใหม่ / Target</span><span className="file-name">{target ? `${target.filename} · ${target.fields.length} fields · ${target.format}` : "เลือกไฟล์ CSV / XLSX / Parquet"}</span><input id="target-file" type="file" accept=".csv,.xlsx,.parquet,.tsv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void inspect("target", file); }} /></label>
        </div>
        <div className="config-grid">
          <label><span>Legacy key</span><select value={legacyKey} disabled={!legacy} onChange={(event) => setLegacyKey(event.target.value)}>{legacy?.fields.map((field) => <option key={field}>{field}</option>)}</select></label>
          <label><span>Target key</span><select value={targetKey} disabled={!target} onChange={(event) => setTargetKey(event.target.value)}>{target?.fields.map((field) => <option key={field}>{field}</option>)}</select></label>
          <label><span>Legacy table <small>สำหรับ SQL เท่านั้น</small></span><input value={legacyTable} onChange={(event) => setLegacyTable(event.target.value)} /></label>
          <label><span>Target table <small>สำหรับ SQL เท่านั้น</small></span><input value={targetTable} onChange={(event) => setTargetTable(event.target.value)} /></label>
          <label className="profile-field"><span>Normalization profile</span><select value={normalizationProfile} onChange={(event) => setNormalizationProfile(event.target.value)}><option value="generic">Generic — conservative text</option><option value="thai_customer">Thai customer — name/phone/tax/date/address</option></select></label>
          <div className="profile-field fuzzy-field"><span>Fuzzy review</span><label className="inline-option"><input type="checkbox" checked={fuzzyEnabled} onChange={(event) => setFuzzyEnabled(event.target.checked)} /> เปิด candidate suggestions</label><small className="muted">แสดงคะแนนเพื่อ review เท่านั้น · ไม่ auto-approve</small></div>
          <label className="profile-field"><span>Review threshold</span><select value={fuzzyThreshold} disabled={!fuzzyEnabled} onChange={(event) => setFuzzyThreshold(event.target.value)}><option value="0.75">75% · exploratory</option><option value="0.90">90% · conservative</option><option value="0.95">95% · strict</option></select></label>
        </div>
        <div className="setup-footer"><span className="helper-text">รองรับ CSV / XLSX / Parquet · profile มีผลเฉพาะค่าที่ใช้เทียบ และเก็บ raw evidence ไว้เหมือนเดิม</span><button className="button primary" onClick={() => void reconcile()} disabled={!canRun || busy}>{busy ? "กำลังตรวจ..." : <>Run reconciliation <span>↗</span></>}</button></div>
        {error && <div className="error-box">{error}</div>}
      </section>

      {result && <section className="panel mapping-panel">
        <div className="panel-heading"><div><span className="section-kicker">02 / FIELD CONTRACT</span><h3>ตรวจ mapping ก่อนเชื่อผล</h3></div><span className="step-label">HEURISTIC SUGGESTIONS</span></div>
        <p className="panel-intro">ระบบเลือกเฉพาะ mapping ที่มั่นใจสูงให้โดยอัตโนมัติ ส่วนรายการอื่นให้คุณตัดสินใจเองแล้วกด Run อีกครั้ง · profile: {result.normalization?.label || normalizationProfile} · fuzzy review: {result.fuzzy_matching?.enabled ? `${Math.round((result.fuzzy_matching.review_threshold || 0.9) * 100)}%` : "off"}</p>
        <div className="mapping-table-wrap"><table className="mapping-table"><thead><tr><th>ใช้</th><th>Legacy field</th><th>Target field</th><th>Confidence</th><th>เหตุผล</th></tr></thead><tbody>
          {suggestions.map((item) => {
            const isKey = item.source === legacyKey;
            const selectedTarget = mapping[item.source] || (item.auto_selected ? item.target || "" : "");
            return <tr key={item.source}><td><input type="checkbox" checked={Boolean(selectedTarget)} disabled={isKey} onChange={(event) => toggleMapping(item.source, event.target.checked, item.target)} /></td><td><code>{item.source}</code>{isKey && <span className="fixed-key"> · key</span>}</td><td><select value={selectedTarget} disabled={isKey} onChange={(event) => setMapping((current) => ({ ...current, [item.source]: event.target.value }))}><option value="">ไม่เลือก field นี้</option>{target?.fields.map((field) => <option key={field}>{field}</option>)}</select></td><td><span className={`confidence${item.confidence < 0.78 ? " low" : ""}`}>{isKey ? "KEY" : `${Math.round(item.confidence * 100)}%`}</span></td><td className="muted">{isKey ? "ใช้ key ที่เลือกเป็นตัวเชื่อม" : item.method}</td></tr>;
          })}
        </tbody></table></div>
      </section>}

      {result && <section className="results-section">
        <div className="summary-grid"><article className="metric-card accent"><span>RECORDS CHECKED</span><strong>{result.summary.records_checked.toLocaleString()}</strong><small>แถวฝั่ง legacy</small></article><article className="metric-card"><span>MATCH</span><strong>{result.summary.matched.toLocaleString()}</strong><small>{result.summary.match_rate}% match rate</small></article><article className="metric-card warn"><span>VALUE MISMATCH</span><strong>{(result.summary.counts.value_mismatch || 0).toLocaleString()}</strong><small>ค่าที่ mapped ไม่ตรง</small></article><article className="metric-card danger"><span>MISSING / DUPLICATE</span><strong>{((result.summary.counts.missing_target || 0) + (result.summary.counts.missing_legacy || 0) + (result.summary.counts.duplicate || 0) + (result.summary.counts.invalid_key || 0)).toLocaleString()}</strong><small>ต้อง review ก่อนปล่อย</small></article></div>
        <div className="panel evidence-panel"><div className="panel-heading evidence-heading"><div><span className="section-kicker">03 / EVIDENCE</span><h3>Exceptions ที่ต้องตัดสินใจ</h3></div><div className="evidence-actions"><select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">ทุกสถานะ</option>{statusOptions.map(([status, count]) => <option key={status} value={status}>{status} · {count}</option>)}</select><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="ค้นหา key..." /><button className="button ghost" onClick={() => download("migration-validation-report.md", makeReport(), "text/markdown;charset=utf-8")}>ดาวน์โหลด report</button><button className="button ghost" onClick={() => { if (result.audit_package) download("migration-validation-audit.json", JSON.stringify(result.audit_package, null, 2), "application/json;charset=utf-8"); }}>ดาวน์โหลด audit package</button><button className="button dark" onClick={() => { if (result.sql) void navigator.clipboard?.writeText(result.sql); }}>คัดลอก SQL</button></div></div>
          <div className="evidence-layout"><div className="evidence-table-wrap"><table className="evidence-table"><thead><tr><th>Key</th><th>Status</th><th>Legacy</th><th>Target</th><th>Reason</th><th>Review</th></tr></thead><tbody>{filteredEvidence.map((item) => <tr key={`${item.key}-${item.status}-${item.reason}`} className={selected === item ? "selected" : ""} onClick={() => setSelected(item)}><td><code>{item.key}</code></td><td><span className={`status-badge status-${item.status}`}>{item.status_label}</span></td><td>{firstValue(item.legacy)}</td><td>{firstValue(item.target)}</td><td className="muted">{item.reason}</td><td><span className={`review-badge review-${reviewStatuses[item.evidence_id] || item.review_status}`}>{reviewLabel(reviewStatuses[item.evidence_id] || item.review_status)}</span></td></tr>)}</tbody></table>{filteredEvidence.length === 0 && <div className="empty-state">ไม่พบรายการตาม filter นี้</div>}</div><aside className="drilldown">{selected ? <><div className="detail-header"><span className="section-kicker">DRILL DOWN</span><span className={`status-badge status-${selected.status}`}>{selected.status_label}</span></div><div className="detail-key">{selected.key}</div><div className="detail-reason">{selected.reason}</div><div className="review-controls"><span className="section-kicker">REVIEW DECISION</span><strong>{reviewLabel(reviewStatuses[selected.evidence_id] || selected.review_status)}</strong><div className="review-buttons"><button className="button ghost" onClick={() => setReviewStatus(selected.evidence_id, "approved")}>Approve</button><button className="button ghost" onClick={() => setReviewStatus(selected.evidence_id, "rejected")}>Reject</button><button className="button ghost" onClick={() => setReviewStatus(selected.evidence_id, "needs-review")}>Needs review</button></div></div>{selected.match_candidates.length > 0 && <div className="candidate-box"><span className="section-kicker">FUZZY CANDIDATES · REVIEW ONLY</span>{selected.match_candidates.map((candidate, index) => { const candidateKey = candidate.candidate_key || candidate.target_key || "(blank)"; return <div className="candidate-row" key={`${candidateKey}-${candidate.row_number}-${index}`}><strong>{candidateKey} · {Math.round(candidate.score * 100)}%</strong><span className="muted">{candidate.reason}</span></div>; })}</div>}<span className="section-kicker">FIELD DIFFERENCES</span>{selected.mismatches.length ? selected.mismatches.map((diff) => <div className="diff-row" key={`${diff.legacy_field}-${diff.target_field}`}><div className="diff-cell"><span>{diff.legacy_field} · legacy</span><strong>{diff.legacy_value || "(blank)"}</strong></div><div className="diff-cell"><span>{diff.target_field} · target</span><strong>{diff.target_value || "(blank)"}</strong></div></div>) : <p className="muted">ไม่มี field ที่เปรียบเทียบแล้วพบความต่าง</p>}</> : <><span className="section-kicker">DRILL DOWN</span><h4>เลือกแถวเพื่อดู evidence</h4><p className="muted">ค่าฝั่งเก่าและใหม่จะแสดงคู่กัน พร้อม field ที่ไม่ตรงและเหตุผลจาก rule ที่ใช้ตรวจ</p></>}</aside></div>
        </div>
      </section>}
      <footer className="footer-note"><span>TRACE / DETERMINISTIC FIRST</span><span>Next.js UI · FastAPI API · DuckDB profile</span></footer>
    </main>
  );
}
