"use client";

import { useParams } from "next/navigation";

import { DocumentResults } from "@/components/documents/document-results";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useAuth } from "@/hooks/use-auth";

export default function DocumentDetailPage() {
  const params = useParams<{ documentId: string }>();
  const { token, loading, error } = useAuth(true);

  if (loading) {
    return <LoadingState label="Loading document…" />;
  }

  if (error || !token || !params.documentId) {
    return <ErrorState message={error ?? "Document could not be loaded."} />;
  }

  return <DocumentResults token={token} documentId={params.documentId} />;
}
