import { ClauseRead } from "@/lib/api/types";

export function ClausesList({ clauses }: { clauses: ClauseRead[] }) {
  return (
    <section className="panel" style={{ padding: "22px" }}>
      <h2 style={{ margin: "0 0 14px", fontSize: "20px" }}>Detected clauses</h2>
      <div style={{ display: "grid", gap: "14px" }}>
        {clauses.length === 0 ? (
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            No clause records were persisted for this version.
          </p>
        ) : null}
        {clauses.map((clause) => (
          <article key={clause.id} style={{ paddingBottom: "14px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "baseline" }}>
              <strong>{clause.title ?? clause.clause_type.replaceAll("_", " ")}</strong>
              <span style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                {Math.round(clause.confidence * 100)}% confidence
              </span>
            </div>
            <p style={{ margin: "8px 0", color: "var(--text-muted)", lineHeight: 1.6 }}>{clause.text}</p>
            <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Type: {clause.clause_type.replaceAll("_", " ")} | Method: {clause.source_method} | Pages{" "}
              {clause.page_start ?? "?"}-{clause.page_end ?? "?"}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
