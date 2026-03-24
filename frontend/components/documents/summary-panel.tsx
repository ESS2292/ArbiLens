import type { ReactNode } from "react";

import { DocumentSummaryResponse } from "@/lib/api/types";
import { StatusBadge } from "@/components/shared/status-badge";

function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="panel" style={{ padding: "22px" }}>
      <h2 style={{ margin: "0 0 14px", fontSize: "20px" }}>{title}</h2>
      {children}
    </section>
  );
}

export function SummaryPanel({ summary }: { summary: DocumentSummaryResponse }) {
  return (
    <div style={{ display: "grid", gap: "18px" }}>
      <section className="panel" style={{ padding: "24px", display: "grid", gap: "8px" }}>
        <span className="badge">Document summary</span>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "34px" }}>Overall risk score: {summary.overall_risk_score}</h1>
            <p style={{ margin: "8px 0 0", color: "var(--text-muted)" }}>
              Based on persisted clause and risk records for version {summary.document_version_id.slice(0, 8)}.
            </p>
          </div>
          <StatusBadge label={summary.generated_from_status} />
        </div>
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "18px" }}>
        <Section title="Top issues">
          <div style={{ display: "grid", gap: "12px" }}>
            {summary.top_issues.map((issue) => (
              <article key={issue.risk_id} style={{ paddingBottom: "12px", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                  <strong>{issue.title}</strong>
                  <StatusBadge label={issue.severity} />
                </div>
                <p style={{ margin: "8px 0", color: "var(--text-muted)", lineHeight: 1.6 }}>
                  {issue.rationale}
                </p>
                <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                  Risk #{issue.risk_id.slice(0, 8)} | Score {issue.score}
                </div>
              </article>
            ))}
          </div>
        </Section>

        <Section title="Negotiation priorities">
          <div style={{ display: "grid", gap: "12px" }}>
            {summary.negotiation_priorities.map((priority) => (
              <article key={priority.risk_id} style={{ padding: "14px", borderRadius: "14px", background: "var(--surface-muted)" }}>
                <div style={{ marginBottom: "6px", fontSize: "13px", color: "var(--text-muted)" }}>
                  Priority {priority.priority_rank}
                </div>
                <strong>{priority.title}</strong>
                <p style={{ margin: "8px 0 0", color: "var(--text-muted)", lineHeight: 1.6 }}>
                  {priority.recommendation}
                </p>
              </article>
            ))}
          </div>
        </Section>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px" }}>
        <Section title="Missing protections">
          <div style={{ display: "grid", gap: "10px" }}>
            {summary.missing_protections.length === 0 ? (
              <p style={{ margin: 0, color: "var(--text-muted)" }}>No missing-protection findings detected.</p>
            ) : (
              summary.missing_protections.map((item) => (
                <div key={item.risk_id} style={{ padding: "12px", borderRadius: "12px", background: "var(--surface-muted)" }}>
                  <strong>{item.title}</strong>
                  <p style={{ margin: "8px 0 0", color: "var(--text-muted)", lineHeight: 1.6 }}>
                    {item.recommendation}
                  </p>
                </div>
              ))
            )}
          </div>
        </Section>

        <Section title="Clause coverage">
          <div style={{ display: "grid", gap: "10px" }}>
            {summary.clause_coverage_summary.map((item) => (
              <div
                key={item.clause_type}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px",
                  borderRadius: "12px",
                  background: item.detected ? "var(--surface-muted)" : "#faf3f1",
                }}
              >
                <span style={{ textTransform: "capitalize" }}>{item.clause_type.replaceAll("_", " ")}</span>
                <strong>{item.detected ? item.clause_count : "Missing"}</strong>
              </div>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}
