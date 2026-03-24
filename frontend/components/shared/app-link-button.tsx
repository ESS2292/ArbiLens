import type { ReactNode } from "react";
import Link from "next/link";

export function AppLinkButton({
  href,
  children,
  secondary = false,
}: {
  href: string;
  children: ReactNode;
  secondary?: boolean;
}) {
  return (
    <Link
      href={href}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "12px 16px",
        borderRadius: "12px",
        fontWeight: 700,
        border: secondary ? "1px solid var(--border)" : "1px solid var(--accent)",
        background: secondary ? "var(--surface)" : "var(--accent)",
        color: secondary ? "var(--text)" : "#fff",
      }}
    >
      {children}
    </Link>
  );
}
