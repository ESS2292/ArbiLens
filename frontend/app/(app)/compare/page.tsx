"use client";

import { ComparisonView } from "@/components/documents/comparison-view";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useAuth } from "@/hooks/use-auth";

export default function ComparePage() {
  const { token, loading, error } = useAuth(true);

  if (loading) {
    return <LoadingState label="Loading comparison tools…" />;
  }

  if (error || !token) {
    return <ErrorState message={error ?? "Authentication is required."} />;
  }

  return <ComparisonView token={token} />;
}
