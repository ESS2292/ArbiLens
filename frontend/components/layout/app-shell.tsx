"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { CurrentUserResponse } from "@/lib/api/types";

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      style={{
        padding: "10px 12px",
        borderRadius: "10px",
        background: active ? "var(--surface-muted)" : "transparent",
        color: active ? "var(--text)" : "var(--text-muted)",
        fontWeight: active ? 700 : 500,
      }}
    >
      {label}
    </Link>
  );
}

export function AppShell({
  currentUser,
  onLogout,
  children,
}: {
  currentUser: CurrentUserResponse | null;
  onLogout: () => void;
  children: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="shell">
      <div className="container" style={{ padding: "24px 0 40px" }}>
        <header
          className="panel"
          style={{
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "24px",
            gap: "16px",
          }}
        >
          <div style={{ display: "grid", gap: "4px" }}>
            <Link href="/dashboard" style={{ fontSize: "22px", fontWeight: 800 }}>
              ArbiLens
            </Link>
            <span style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              {currentUser?.organization.name ?? "Workspace"}
            </span>
          </div>
          <nav style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <NavLink href="/dashboard" label="Dashboard" active={pathname === "/dashboard"} />
            <NavLink href="/documents" label="Documents" active={pathname === "/documents"} />
            <NavLink
              href="/documents/upload"
              label="Upload"
              active={pathname === "/documents/upload"}
            />
            <NavLink href="/compare" label="Compare" active={pathname === "/compare"} />
            <NavLink href="/billing" label="Billing" active={pathname === "/billing"} />
          </nav>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontWeight: 700 }}>{currentUser?.full_name}</div>
              <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                {currentUser?.email}
              </div>
            </div>
            <button
              type="button"
              onClick={onLogout}
              style={{
                height: "40px",
                borderRadius: "10px",
                border: "1px solid var(--border)",
                background: "var(--surface)",
                padding: "0 14px",
                cursor: "pointer",
              }}
            >
              Log out
            </button>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
