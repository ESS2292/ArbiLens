"use client";

import { useEffect, useState } from "react";

import { apiClient, ApiClientError } from "@/lib/api/client";
import { ReportRead } from "@/lib/api/types";
import { AppLinkButton } from "@/components/shared/app-link-button";

export function ReportActions({
  token,
  documentId,
  canGenerate,
}: {
  token: string;
  documentId: string;
  canGenerate: boolean;
}) {
  const [reports, setReports] = useState<ReportRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .getReports(token, documentId)
      .then(setReports)
      .catch(() => setReports([]));
  }, [documentId, token]);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.generateReport(token, documentId);
      setReports((current) => [response.report, ...current.filter((item) => item.id !== response.report.id)]);
      window.open(response.download_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Report generation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel" style={{ padding: "22px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: "0 0 6px", fontSize: "20px" }}>PDF report</h2>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Generate a downloadable contract risk report from completed analysis data.
          </p>
        </div>
        {canGenerate ? (
          <button
            type="button"
            onClick={handleGenerate}
            disabled={loading}
            style={{
              height: "44px",
              borderRadius: "12px",
              border: 0,
              padding: "0 16px",
              background: "var(--accent)",
              color: "#fff",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {loading ? "Generating…" : "Generate report"}
          </button>
        ) : (
          <AppLinkButton href="/billing">Upgrade for reports</AppLinkButton>
        )}
      </div>
      {error ? <p style={{ color: "#9b2c2c" }}>{error}</p> : null}
      <div style={{ marginTop: "14px", display: "grid", gap: "10px" }}>
        {reports.map((report) => (
          <div
            key={report.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: "12px",
              padding: "12px",
              borderRadius: "12px",
              background: "var(--surface-muted)",
            }}
          >
            <div>
              <strong>{report.filename}</strong>
              <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                {report.generated_at ? new Date(report.generated_at).toLocaleString() : "Pending"}
              </div>
            </div>
            <button
              type="button"
              onClick={async () => {
                try {
                  const next = await apiClient.getReport(token, report.id);
                  window.open(next.download_url, "_blank", "noopener,noreferrer");
                } catch (err) {
                  setError(err instanceof ApiClientError ? err.message : "Failed to open report.");
                }
              }}
              style={{
                border: "1px solid var(--border)",
                borderRadius: "10px",
                background: "var(--surface)",
                padding: "0 14px",
                cursor: "pointer",
              }}
            >
              Open
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
