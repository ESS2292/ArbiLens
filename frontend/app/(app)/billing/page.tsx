"use client";

import { BillingPanel } from "@/components/billing/billing-panel";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useAuth } from "@/hooks/use-auth";

export default function BillingPage() {
  const { token, loading, error } = useAuth(true);

  if (loading) {
    return <LoadingState label="Loading billing page…" />;
  }

  if (error || !token) {
    return <ErrorState message={error ?? "Authentication is required."} />;
  }

  return <BillingPanel token={token} />;
}
