"use client";

import { useEffect, useState } from "react";

import { apiClient, ApiClientError } from "@/lib/api/client";
import {
  BillingStatusResponse,
  ClauseRead,
  DocumentDetailResponse,
  DocumentSummaryResponse,
  RiskRead,
} from "@/lib/api/types";
import { useDocumentStatus } from "@/hooks/use-document-status";
import { ClausesList } from "@/components/documents/clauses-list";
import { ReportActions } from "@/components/documents/report-actions";
import { RisksList } from "@/components/documents/risks-list";
import { SummaryPanel } from "@/components/documents/summary-panel";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { StatusBadge } from "@/components/shared/status-badge";

export function DocumentResults({
  token,
  documentId,
}: {
  token: string;
  documentId: string;
}) {
  const { status, loading: statusLoading, error: statusError } = useDocumentStatus(token, documentId);
  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null);
  const [summary, setSummary] = useState<DocumentSummaryResponse | null>(null);
  const [clauses, setClauses] = useState<ClauseRead[]>([]);
  const [risks, setRisks] = useState<RiskRead[]>([]);
  const [billing, setBilling] = useState<BillingStatusResponse | null>(null);
  const [resultsPending, setResultsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadBase() {
      setLoading(true);
      try {
        const [nextDetail, nextBilling] = await Promise.all([
          apiClient.getDocument(token, documentId),
          apiClient.getBillingStatus(token).catch(() => null),
        ]);
        if (!cancelled) {
          setDetail(nextDetail);
          setBilling(nextBilling);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiClientError ? err.message : "Failed to load document.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadBase();
    return () => {
      cancelled = true;
    };
  }, [documentId, token]);

  useEffect(() => {
    if (!status || status.document_status !== "completed") {
      return;
    }

    let cancelled = false;
    async function loadResults() {
      try {
        const [nextSummary, nextClauses, nextRisks] = await Promise.all([
          apiClient.getDocumentSummary(token, documentId),
          apiClient.getDocumentClauses(token, documentId),
          apiClient.getDocumentRisks(token, documentId),
        ]);
        if (!cancelled) {
          setResultsPending(false);
          setSummary(nextSummary);
          setClauses(nextClauses);
          setRisks(nextRisks);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiClientError && err.code === "summary_not_ready") {
            setResultsPending(true);
            setError(null);
            return;
          }
          setError(err instanceof ApiClientError ? err.message : "Failed to load results.");
        }
      }
    }

    void loadResults();
    return () => {
      cancelled = true;
    };
  }, [documentId, status, token]);

  if (loading || statusLoading) {
    return <LoadingState label="Loading document results…" />;
  }

  if (error || statusError || !detail || !status) {
    return <ErrorState message={error ?? statusError ?? "Document could not be loaded."} />;
  }

  return (
    <div style={{ display: "grid", gap: "18px" }}>
      <section className="panel" style={{ padding: "24px", display: "grid", gap: "8px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "32px" }}>{detail.filename}</h1>
            <p style={{ margin: "8px 0 0", color: "var(--text-muted)" }}>
              Current stage: {status.current_stage.replaceAll("_", " ")}
            </p>
          </div>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <StatusBadge label={status.document_status} />
            <StatusBadge label={status.job_status} />
          </div>
        </div>
      </section>

      {status.document_status === "failed" ? (
        <ErrorState
          title="Analysis failed"
          message={`The pipeline stopped during ${status.error_stage ?? "processing"} with code ${status.error_code ?? "unknown_error"}.`}
        />
      ) : null}

      {status.document_status !== "completed" ? (
        <section className="panel" style={{ padding: "24px" }}>
          <h2 style={{ margin: "0 0 8px", fontSize: "22px" }}>Processing in progress</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.6 }}>
            ArbiLens is still parsing, extracting clauses, or scoring risks. This page polls for status updates automatically.
          </p>
        </section>
      ) : null}

      {status.document_status === "completed" && resultsPending ? (
        <section className="panel" style={{ padding: "24px" }}>
          <h2 style={{ margin: "0 0 8px", fontSize: "22px" }}>Finalizing results</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.6 }}>
            Core analysis has completed. ArbiLens is finishing result aggregation and evidence packaging for display.
          </p>
        </section>
      ) : null}

      {status.document_status === "completed" && summary ? (
        <>
          <ReportActions
            token={token}
            documentId={documentId}
            canGenerate={billing?.premium_access ?? false}
          />
          <SummaryPanel summary={summary} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px" }}>
            <ClausesList clauses={clauses} />
            <RisksList risks={risks} />
          </div>
        </>
      ) : null}
    </div>
  );
}
