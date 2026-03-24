"use client";

import { useEffect, useState } from "react";

import { apiClient, ApiClientError } from "@/lib/api/client";
import { BillingStatusResponse } from "@/lib/api/types";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";

export function BillingPanel({ token }: { token: string }) {
  const [billing, setBilling] = useState<BillingStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<"checkout" | "portal" | null>(null);

  useEffect(() => {
    apiClient
      .getBillingStatus(token)
      .then(setBilling)
      .catch((err: unknown) =>
        setError(err instanceof ApiClientError ? err.message : "Failed to load billing status."),
      )
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return <LoadingState label="Loading billing…" />;
  }

  if (error || !billing) {
    return <ErrorState message={error ?? "Billing could not be loaded."} />;
  }

  return (
    <section className="panel" style={{ padding: "24px", display: "grid", gap: "16px" }}>
      <div>
        <h1 style={{ margin: "0 0 8px", fontSize: "30px" }}>Billing</h1>
        <p style={{ margin: 0, color: "var(--text-muted)" }}>
          Reports and comparison are premium features gated by the organization subscription state.
        </p>
      </div>
      <div style={{ display: "grid", gap: "8px" }}>
        <div>Subscription status: <strong>{billing.subscription_status}</strong></div>
        <div>Premium access: <strong>{billing.premium_access ? "Enabled" : "Disabled"}</strong></div>
      </div>
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={async () => {
            setActionLoading("checkout");
            setError(null);
            try {
              const session = await apiClient.createCheckoutSession(token);
              window.location.href = session.checkout_url;
            } catch (err) {
              setError(err instanceof ApiClientError ? err.message : "Failed to create checkout session.");
            } finally {
              setActionLoading(null);
            }
          }}
          disabled={actionLoading !== null}
          style={{ height: "46px", border: 0, borderRadius: "12px", padding: "0 16px", background: "var(--accent)", color: "#fff", fontWeight: 700 }}
        >
          {actionLoading === "checkout" ? "Redirecting…" : "Start subscription"}
        </button>
        {billing.stripe_customer_id ? (
          <button
            type="button"
            onClick={async () => {
              setActionLoading("portal");
              setError(null);
              try {
                const portal = await apiClient.createCustomerPortalSession(token);
                window.location.href = portal.portal_url;
              } catch (err) {
                setError(err instanceof ApiClientError ? err.message : "Failed to open customer portal.");
              } finally {
                setActionLoading(null);
              }
            }}
            disabled={actionLoading !== null}
            style={{ height: "46px", border: "1px solid var(--border)", borderRadius: "12px", padding: "0 16px", background: "var(--surface)", fontWeight: 700 }}
          >
            {actionLoading === "portal" ? "Opening…" : "Open customer portal"}
          </button>
        ) : null}
      </div>
    </section>
  );
}
