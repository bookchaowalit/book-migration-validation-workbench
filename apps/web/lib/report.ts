export type ReviewStatus = "unreviewed" | "approved" | "rejected" | "needs-review";

type ReportData = {
  summary: {
    records_checked: number;
    match_rate: number;
    exceptions: number;
    counts: Record<string, number>;
  };
  evidence: Array<{ evidence_id: string; key: string; review_status: ReviewStatus }>;
  configuration_fingerprint: string;
  normalization?: { name: string };
  fuzzy_matching?: { enabled: boolean; review_threshold: number };
};

type ReportResult = {
  redacted_export?: ReportData | null;
  audit_package?: { fingerprints: { audit_package_sha256?: string } };
};

export function buildRedactedReport(
  result: ReportResult,
  reviewStatuses: Record<string, ReviewStatus>,
  options: { generatedAt?: Date } = {},
): string {
  const redacted = result.redacted_export;
  if (!redacted || !Array.isArray(redacted.evidence)) {
    throw new Error("ไม่พบข้อมูลที่ปกปิดสำหรับ export กรุณารันการตรวจใหม่");
  }
  const reviewLabels: Record<ReviewStatus, string> = {
    unreviewed: "ยังไม่ review",
    approved: "อนุมัติ",
    rejected: "ไม่อนุมัติ",
    "needs-review": "ต้องตรวจเพิ่ม",
  };
  const lines = [
    "# Migration Validation Report",
    "",
    `- Generated: ${(options.generatedAt || new Date()).toISOString()}`,
    // Filenames and field mappings are omitted: the server's field-profile
    // redaction masks evidence values, but does not sanitize this metadata.
    `- Records checked: ${redacted.summary.records_checked}`,
    `- Match rate: ${redacted.summary.match_rate}%`,
    `- Exceptions: ${redacted.summary.exceptions}`,
    `- Configuration fingerprint: ${redacted.configuration_fingerprint}`,
    `- Audit package fingerprint: ${result.audit_package?.fingerprints.audit_package_sha256 || "not available"}`,
    `- Normalization profile: ${redacted.normalization?.name || "not available"}`,
    `- Fuzzy review: ${redacted.fuzzy_matching?.enabled ? `enabled at ${Math.round(redacted.fuzzy_matching.review_threshold * 100)}%` : "disabled"} · auto-approval: false`,
    "- Export mode: field-profile redacted",
    "",
    "## Status counts",
    "",
    ...Object.entries(redacted.summary.counts).map(([status, count]) => `- ${status}: ${count}`),
    "",
    "## Review status",
    "",
    ...redacted.evidence.map((item) => `- ${item.key}: ${reviewLabels[reviewStatuses[item.evidence_id] || item.review_status]}`),
  ];
  return lines.join("\n");
}
