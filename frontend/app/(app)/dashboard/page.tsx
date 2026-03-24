"use client";

import { useEffect, useState } from "react";

import { AppLinkButton } from "@/components/shared/app-link-button";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { DocumentsTable } from "@/components/documents/documents-table";
import { DashboardData } from "@/lib/api/types";
import { apiClient, ApiClientError } from "@/lib/api/client";
import { useAuth } from "@/hooks/use-auth";

export default function DashboardPage() {
  const { token, user, loading: authLoading } = useAuth(true);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    apiClient
      .getDashboardData(token)
      .then((nextData) => setData(nextData))
      .catch((err: unknown) =>
        setError(err instanceof ApiClientError ? err.message : "Failed to load dashboard."),
      )
      .finally(() => setLoading(false));
  }, [token]);

  if (authLoading || loading) {
    return <LoadingState label="Loading dashboard…" />;
  }

  if (error || !data || !user) {
    return <ErrorState message={error ?? "Dashboard could not be loaded."} />;
  }

  return (
    <div style={{ display: "grid", gap: "20px" }}>
      <section className="panel" style={{ padding: "24px", display: "grid", gap: "10px" }}>
        <span className="badge">Workspace overview</span>
        <h1 style={{ margin: 0, fontSize: "34px" }}>Contract review operations</h1>
        <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.6 }}>
          Signed in as {user.full_name}. Upload new contracts, monitor processing status, and review deterministic risk findings.
        </p>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <AppLinkButton href="/documents/upload">Upload contract</AppLinkButton>
          <AppLinkButton href="/documents" secondary>
            Open document list
          </AppLinkButton>
        </div>
      </section>

      {data.documents.length === 0 ? (
        <EmptyState
          title="No documents yet"
          message="Upload your first contract to begin parsing, clause extraction, and risk analysis."
          action={<AppLinkButton href="/documents/upload">Upload first contract</AppLinkButton>}
        />
      ) : (
        <DocumentsTable documents={data.documents.slice(0, 5)} />
      )}
    </div>
  );
}
