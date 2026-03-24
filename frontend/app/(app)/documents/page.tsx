"use client";

import { useEffect, useState } from "react";

import { AppLinkButton } from "@/components/shared/app-link-button";
import { DocumentsTable } from "@/components/documents/documents-table";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { apiClient, ApiClientError } from "@/lib/api/client";
import { DocumentListItem } from "@/lib/api/types";
import { useAuth } from "@/hooks/use-auth";

export default function DocumentsPage() {
  const { token, loading: authLoading } = useAuth(true);
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    apiClient
      .getDocuments(token)
      .then(setDocuments)
      .catch((err: unknown) =>
        setError(err instanceof ApiClientError ? err.message : "Failed to load documents."),
      )
      .finally(() => setLoading(false));
  }, [token]);

  if (authLoading || loading) {
    return <LoadingState label="Loading documents…" />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  return documents.length === 0 ? (
    <EmptyState
      title="No uploaded contracts"
      message="Once documents are uploaded, they appear here with live processing state and overall scores."
      action={<AppLinkButton href="/documents/upload">Upload contract</AppLinkButton>}
    />
  ) : (
    <div style={{ display: "grid", gap: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "30px" }}>Documents</h1>
          <p style={{ margin: "8px 0 0", color: "var(--text-muted)" }}>
            Review processing state, summaries, clauses, and risk findings.
          </p>
        </div>
        <AppLinkButton href="/documents/upload">Upload contract</AppLinkButton>
      </div>
      <DocumentsTable documents={documents} />
    </div>
  );
}
