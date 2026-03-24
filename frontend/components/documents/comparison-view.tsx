"use client";

import { useEffect, useState } from "react";

import { apiClient, ApiClientError } from "@/lib/api/client";
import { BillingStatusResponse, ComparisonResponse, DocumentListItem } from "@/lib/api/types";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { AppLinkButton } from "@/components/shared/app-link-button";

export function ComparisonView({ token }: { token: string }) {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [billing, setBilling] = useState<BillingStatusResponse | null>(null);
  const [leftDocumentId, setLeftDocumentId] = useState("");
  const [rightDocumentId, setRightDocumentId] = useState("");
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiClient.getDocuments(token),
      apiClient.getBillingStatus(token).catch(() => null),
    ])
      .then(([items, nextBilling]) => {
        const completed = items.filter((item) => item.status === "completed");
        setDocuments(completed);
        setBilling(nextBilling);
        setLeftDocumentId(completed[0]?.id ?? "");
        setRightDocumentId(completed[1]?.id ?? "");
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiClientError ? err.message : "Failed to load comparable documents."),
      )
      .finally(() => setLoading(false));
  }, [token]);

  async function handleCompare() {
    if (!leftDocumentId || !rightDocumentId) {
      setError("Select two completed documents to compare.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.compareDocuments(token, leftDocumentId, rightDocumentId);
      setComparison(result);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Comparison failed.");
    } finally {
      setLoading(false);
    }
  }

  if (loading && documents.length === 0) {
    return <LoadingState label="Loading comparison workspace…" />;
  }

  if (error && !comparison && documents.length === 0) {
    return <ErrorState message={error} />;
  }

  if (billing && !billing.premium_access) {
    return (
      <section className="panel" style={{ padding: "24px", display: "grid", gap: "14px" }}>
        <div>
          <h1 style={{ margin: "0 0 8px", fontSize: "30px" }}>Contract comparison</h1>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Comparison is available on active paid subscriptions because it depends on completed, stored analysis data.
          </p>
        </div>
        <AppLinkButton href="/billing">Open billing</AppLinkButton>
      </section>
    );
  }

  return (
    <div style={{ display: "grid", gap: "18px" }}>
      <section className="panel" style={{ padding: "24px", display: "grid", gap: "14px" }}>
        <div>
          <h1 style={{ margin: "0 0 8px", fontSize: "30px" }}>Contract comparison</h1>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Compare two completed analyses to identify changed clauses, protections, and risk movement.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "12px" }}>
          <select value={leftDocumentId} onChange={(event) => setLeftDocumentId(event.target.value)} style={{ height: "44px", borderRadius: "12px", border: "1px solid var(--border)", padding: "0 12px" }}>
            {documents.map((document) => (
              <option key={document.id} value={document.id}>
                {document.filename}
              </option>
            ))}
          </select>
          <select value={rightDocumentId} onChange={(event) => setRightDocumentId(event.target.value)} style={{ height: "44px", borderRadius: "12px", border: "1px solid var(--border)", padding: "0 12px" }}>
            {documents.map((document) => (
              <option key={document.id} value={document.id}>
                {document.filename}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleCompare}
            disabled={!leftDocumentId || !rightDocumentId || leftDocumentId === rightDocumentId}
            style={{ border: 0, borderRadius: "12px", padding: "0 18px", background: "var(--accent)", color: "#fff", fontWeight: 700 }}
          >
            Compare
          </button>
        </div>
        {error ? <p style={{ margin: 0, color: "#9b2c2c" }}>{error}</p> : null}
      </section>

      {comparison ? (
        <>
          <section className="panel" style={{ padding: "22px" }}>
            <h2 style={{ margin: "0 0 10px", fontSize: "22px" }}>
              Score delta: {comparison.left_overall_score} to {comparison.right_overall_score}
            </h2>
            <p style={{ margin: 0, color: "var(--text-muted)" }}>
              Change: {comparison.score_delta > 0 ? "+" : ""}
              {comparison.score_delta}
            </p>
          </section>

          <section className="panel" style={{ padding: "22px" }}>
            <h2 style={{ margin: "0 0 12px", fontSize: "20px" }}>Protection changes</h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <div>
                <strong>Protections removed</strong>
                <ul>
                  {comparison.protections_removed.map((item) => (
                    <li key={item}>{item.replaceAll("_", " ")}</li>
                  ))}
                  {comparison.protections_removed.length === 0 ? <li>None detected</li> : null}
                </ul>
              </div>
              <div>
                <strong>Protections added</strong>
                <ul>
                  {comparison.protections_added.map((item) => (
                    <li key={item}>{item.replaceAll("_", " ")}</li>
                  ))}
                  {comparison.protections_added.length === 0 ? <li>None detected</li> : null}
                </ul>
              </div>
            </div>
          </section>

          <section className="panel" style={{ padding: "22px" }}>
            <h2 style={{ margin: "0 0 12px", fontSize: "20px" }}>Risk changes</h2>
            <div style={{ display: "grid", gap: "12px" }}>
              {comparison.risk_differences.map((risk) => (
                <article key={`${risk.category}-${risk.title}`} style={{ borderBottom: "1px solid var(--border)", paddingBottom: "12px" }}>
                  <strong>{risk.title}</strong>
                  <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                    {risk.change_type.replaceAll("_", " ")} | {risk.left_severity ?? "n/a"} {risk.left_score ?? "-"} -> {risk.right_severity ?? "n/a"} {risk.right_score ?? "-"}
                  </div>
                  <p style={{ margin: "8px 0 0", color: "var(--text-muted)" }}>{risk.explanation}</p>
                </article>
              ))}
              {comparison.risk_differences.length === 0 ? (
                <p style={{ margin: 0, color: "var(--text-muted)" }}>No material risk movement detected.</p>
              ) : null}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
