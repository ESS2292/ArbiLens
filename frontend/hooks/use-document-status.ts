"use client";

import { useEffect, useState } from "react";

import { apiClient, ApiClientError } from "@/lib/api/client";
import { DocumentStatusResponse } from "@/lib/api/types";
import { shouldPollStatus } from "@/lib/documents";

export function useDocumentStatus(token: string | null, documentId: string) {
  const [status, setStatus] = useState<DocumentStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    let intervalId: number | undefined;

    const loadStatus = async () => {
      try {
        const nextStatus = await apiClient.getDocumentStatus(token, documentId);
        if (cancelled) return;
        setStatus(nextStatus);
        setError(null);
        if (!shouldPollStatus(nextStatus) && intervalId) {
          window.clearInterval(intervalId);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setError(err instanceof ApiClientError ? err.message : "Failed to load status.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadStatus();
    intervalId = window.setInterval(() => {
      void loadStatus();
    }, 5000);

    return () => {
      cancelled = true;
      if (intervalId) {
        window.clearInterval(intervalId);
      }
    };
  }, [documentId, token]);

  return { status, loading, error };
}
