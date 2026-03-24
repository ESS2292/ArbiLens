"use client";

import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { UploadForm } from "@/components/documents/upload-form";
import { useAuth } from "@/hooks/use-auth";

export default function UploadDocumentPage() {
  const { token, loading, error } = useAuth(true);

  if (loading) {
    return <LoadingState label="Loading upload form…" />;
  }

  if (error || !token) {
    return <ErrorState message={error ?? "Authentication is required."} />;
  }

  return <UploadForm token={token} />;
}
