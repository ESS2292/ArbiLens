import { RiskRead } from "@/lib/api/types";
import { StatusBadge } from "@/components/shared/status-badge";

export function RisksList({ risks }: { risks: RiskRead[] }) {
  return (
    <section className="panel" style={{ padding: "22px" }}>
      <h2 style={{ margin: "0 0 14px", fontSize: "20px" }}>Risk findings</h2>
      <div style={{ display: "grid", gap: "16px" }}>
        {risks.length === 0 ? (
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            No risk findings were generated for this version.
          </p>
        ) : null}
        {risks.map((risk) => (
          <article key={risk.id} style={{ paddingBottom: "16px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
              <div>
                <strong>{risk.title}</strong>
                <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                  {risk.category.replaceAll("_", " ")} | Score {risk.score}
                </div>
              </div>
              <StatusBadge label={risk.severity} />
            </div>
            <p style={{ margin: "10px 0 6px", color: "var(--text-muted)", lineHeight: 1.6 }}>
              {risk.summary}
            </p>
            <p style={{ margin: "0 0 6px", lineHeight: 1.6 }}>{risk.rationale}</p>
            <p style={{ margin: "0 0 8px", color: "var(--text-muted)", lineHeight: 1.6 }}>
              Recommendation: {risk.recommendation}
            </p>
            <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Evidence: {risk.evidence_text ?? "Derived from missing or clause-level rule."}
            </div>
            <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Trace: rule {risk.deterministic_rule_code ?? "n/a"} | citations {risk.citations.length}
            </div>
            {risk.citations.length > 0 ? (
              <div style={{ marginTop: "6px", fontSize: "13px", color: "var(--text-muted)" }}>
                Sources:{" "}
                {risk.citations
                  .map((citation) => {
                    const pageStart = citation.page_start;
                    const pageEnd = citation.page_end;
                    const pageLabel =
                      typeof pageStart === "number"
                        ? `pages ${pageStart}-${typeof pageEnd === "number" ? pageEnd : pageStart}`
                        : "document context";
                    return `${citation.reference_type ?? "reference"} (${pageLabel})`;
                  })
                  .join(", ")}
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
