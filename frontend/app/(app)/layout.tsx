"use client";

import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { useAuth } from "@/hooks/use-auth";

export default function AuthenticatedLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  const { user, loading, error, logout } = useAuth(true);

  if (loading) {
    return <LoadingState label="Loading workspace…" />;
  }

  if (error || !user) {
    return <ErrorState message={error ?? "Authentication is required."} />;
  }

  return (
    <AppShell currentUser={user} onLogout={logout}>
      {children}
    </AppShell>
  );
}
