"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient, ApiClientError } from "@/lib/api/client";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/auth-storage";
import { CurrentUserResponse } from "@/lib/api/types";

export function useAuth(required = true) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<CurrentUserResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(required);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const existingToken = getStoredToken();
    setToken(existingToken);
    if (!existingToken) {
      setLoading(false);
      if (required) {
        router.replace("/login");
      }
      return;
    }

    apiClient
      .getCurrentUser(existingToken)
      .then((currentUser) => {
        setUser(currentUser);
        setError(null);
      })
      .catch((err: unknown) => {
        clearStoredToken();
        setToken(null);
        setUser(null);
        setError(err instanceof ApiClientError ? err.message : "Authentication failed.");
        if (required) {
          router.replace("/login");
        }
      })
      .finally(() => setLoading(false));
  }, [required, router]);

  function persistSession(nextToken: string, nextUser: CurrentUserResponse | null = null) {
    setStoredToken(nextToken);
    setToken(nextToken);
    if (nextUser) {
      setUser(nextUser);
    }
  }

  function logout() {
    clearStoredToken();
    setToken(null);
    setUser(null);
    router.replace("/login");
  }

  return { token, user, loading, error, persistSession, logout };
}
