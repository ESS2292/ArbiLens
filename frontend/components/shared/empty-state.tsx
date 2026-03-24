import type { ReactNode } from "react";

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="panel" style={{ padding: "28px", textAlign: "center" }}>
      <h2 style={{ margin: "0 0 8px", fontSize: "22px" }}>{title}</h2>
      <p style={{ margin: "0 0 16px", color: "var(--text-muted)", lineHeight: 1.6 }}>
        {message}
      </p>
      {action}
    </div>
  );
}
