import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { buildRedactedReport } from "../lib/report.ts";

const evidence = (id, key, review_status = "unreviewed") => ({ evidence_id: id, key, review_status });

function resultFixture() {
  const safe = {
    summary: { records_checked: 2, match_rate: 50, exceptions: 1, counts: { match: 1, value_mismatch: 1 } },
    evidence: [evidence("row-a", "[REDACTED]"), evidence("row-b", "[REDACTED]", "rejected")],
    applied_mapping: { email: "email" },
    configuration_fingerprint: "a".repeat(64),
    normalization: { name: "generic" },
    fuzzy_matching: { enabled: true, review_threshold: 0.9 },
    input: { legacy: { filename: "PRIVATE_SOURCE_NAME.xlsx" }, target: { filename: "PRIVATE_TARGET_NAME.xlsx" } },
  };
  return {
    ...safe,
    evidence: [evidence("row-a", "SYNTHETIC_PRIVATE_KEY_A"), evidence("row-b", "SYNTHETIC_PRIVATE_KEY_B")],
    applied_mapping: { SYNTHETIC_PRIVATE_FIELD: "SYNTHETIC_PRIVATE_COLUMN" },
    redacted_export: safe,
    audit_package: { fingerprints: { audit_package_sha256: "b".repeat(64) } },
  };
}

const generatedAt = new Date("2026-10-13T00:00:00.000Z");

test("report uses sanitized keys and latest review by evidence_id despite identical masked keys", () => {
  const result = resultFixture();
  const original = structuredClone(result);
  const report = buildRedactedReport(result, { "row-a": "approved", "row-b": "needs-review" }, { generatedAt });
  assert.ok(!report.includes("SYNTHETIC_PRIVATE_KEY"));
  assert.ok(report.includes("- [REDACTED]: อนุมัติ\n- [REDACTED]: ต้องตรวจเพิ่ม"));
  assert.deepEqual(result, original);
});

test("report metadata omits filenames and raw field identifiers", () => {
  const report = buildRedactedReport(resultFixture(), {}, {
    generatedAt,
    legacyFilename: "PRIVATE_SOURCE_NAME.xlsx",
    targetFilename: "PRIVATE_TARGET_NAME.xlsx",
  });
  for (const marker of ["PRIVATE_SOURCE_NAME", "PRIVATE_TARGET_NAME", "SYNTHETIC_PRIVATE_FIELD", "SYNTHETIC_PRIVATE_COLUMN"]) {
    assert.ok(!report.includes(marker), `Report leaked ${marker}`);
  }
  assert.ok(report.includes(`Configuration fingerprint: ${"a".repeat(64)}`));
  assert.ok(report.includes(`Audit package fingerprint: ${"b".repeat(64)}`));
});

test("report summary and review fallback come from the sanitized copy", () => {
  const result = resultFixture();
  result.summary = { ...result.summary, records_checked: 999 };
  result.normalization = { name: "SYNTHETIC_PRIVATE_PROFILE" };
  const report = buildRedactedReport(result, {}, { generatedAt });
  assert.ok(report.includes("Records checked: 2"));
  assert.ok(!report.includes("Records checked: 999"));
  assert.ok(!report.includes("SYNTHETIC_PRIVATE_PROFILE"));
  assert.ok(report.includes("- [REDACTED]: ยังไม่ review\n- [REDACTED]: ไม่อนุมัติ"));
  assert.ok(report.includes("Generated: 2026-10-13T00:00:00.000Z"));
});

for (const redacted_export of [undefined, null]) {
  test(`report refuses export when sanitized copy is ${redacted_export}`, () => {
    assert.throws(() => buildRedactedReport({ ...resultFixture(), redacted_export }, {}, { generatedAt }), /ปกปิด/);
  });
}

test("report preserves an allowed key supplied by the server's redaction policy", () => {
  const result = resultFixture();
  result.redacted_export.evidence = [evidence("row-a", "public-record", "approved")];
  const report = buildRedactedReport(result, {}, { generatedAt });
  assert.ok(report.includes("- public-record: อนุมัติ"));
  assert.ok(!report.includes("SYNTHETIC_PRIVATE_KEY"));
});

// Execute the production click handler as well as the pure builder, with
// only its browser download/error sinks replaced. This covers the refusal
// path without introducing a browser or another test dependency.
const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const handler = page.match(/  function downloadReport\(\) \{[\s\S]*?\n  \}/)?.[0];
assert.ok(handler, "Production report handler must be available");
const invokeDownload = new Function("result", "reviewStatuses", "download", "setError", "buildRedactedReport", `${handler}; downloadReport();`);

for (const redacted_export of [undefined, null]) {
  test(`report click refuses download and surfaces UI error when sanitized copy is ${redacted_export}`, () => {
    const downloads = [];
    const errors = [];
    invokeDownload({ ...resultFixture(), redacted_export }, {}, (...args) => downloads.push(args), (error) => errors.push(error), buildRedactedReport);
    assert.equal(downloads.length, 0);
    assert.equal(errors.length, 1);
    assert.match(errors[0], /ปกปิด/);
  });
}

test("report click downloads sanitized Markdown with the latest review statuses", () => {
  const downloads = [];
  const errors = [];
  invokeDownload(resultFixture(), { "row-a": "approved" }, (...args) => downloads.push(args), (error) => errors.push(error), buildRedactedReport);
  assert.equal(downloads.length, 1);
  assert.equal(errors.length, 0);
  const [filename, content, contentType] = downloads[0];
  assert.equal(filename, "migration-validation-report.md");
  assert.equal(contentType, "text/markdown;charset=utf-8");
  assert.ok(content.includes("- [REDACTED]: อนุมัติ"));
  assert.ok(!content.includes("SYNTHETIC_PRIVATE_KEY"));
});
