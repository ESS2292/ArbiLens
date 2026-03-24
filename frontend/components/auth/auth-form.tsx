"use client";

import type { ReactNode } from "react";
import { FormEvent, useState } from "react";

export type AuthField = {
  name: string;
  label: string;
  type?: string;
  autoComplete?: string;
};

export function AuthForm({
  title,
  subtitle,
  fields,
  submitLabel,
  loadingLabel,
  onSubmit,
  footer,
}: {
  title: string;
  subtitle: string;
  fields: AuthField[];
  submitLabel: string;
  loadingLabel: string;
  onSubmit: (values: Record<string, string>) => Promise<void>;
  footer: ReactNode;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="panel" style={{ padding: "32px", width: "min(480px, 100%)" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: "0 0 8px", fontSize: "32px" }}>{title}</h1>
        <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.6 }}>{subtitle}</p>
      </div>
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "16px" }}>
        {fields.map((field) => (
          <label key={field.name} style={{ display: "grid", gap: "8px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600 }}>{field.label}</span>
            <input
              required
              type={field.type ?? "text"}
              autoComplete={field.autoComplete}
              value={values[field.name] ?? ""}
              onChange={(event) =>
                setValues((current) => ({ ...current, [field.name]: event.target.value }))
              }
              style={{
                height: "46px",
                borderRadius: "12px",
                border: "1px solid var(--border)",
                padding: "0 14px",
                background: "var(--surface)",
                color: "var(--text)",
              }}
            />
          </label>
        ))}
        {error ? <p style={{ margin: 0, color: "#9b2c2c" }}>{error}</p> : null}
        <button
          type="submit"
          disabled={submitting}
          style={{
            height: "48px",
            border: 0,
            borderRadius: "12px",
            background: "var(--accent)",
            color: "#fff",
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          {submitting ? loadingLabel : submitLabel}
        </button>
      </form>
      <div style={{ marginTop: "20px", color: "var(--text-muted)" }}>{footer}</div>
    </div>
  );
}
