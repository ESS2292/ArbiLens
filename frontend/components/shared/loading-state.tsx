export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="panel" style={{ padding: "24px", color: "var(--text-muted)" }}>
      {label}
    </div>
  );
}
