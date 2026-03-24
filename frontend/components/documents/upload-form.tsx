"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient, ApiClientError } from "@/lib/api/client";

export function UploadForm({ token }: { token: string }) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Select a PDF or DOCX file.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const result = await apiClient.uploadDocument(token, file);
      router.push(`/documents/${result.document_id}`);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="panel" style={{ padding: "28px", display: "grid", gap: "18px" }}>
      <div>
        <h1 style={{ margin: "0 0 8px", fontSize: "30px" }}>Upload contract</h1>
        <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.6 }}>
          Submit a PDF or DOCX file. Parsing, clause extraction, and scoring run in the background.
        </p>
      </div>
      <label
        style={{
          display: "grid",
          gap: "8px",
          padding: "20px",
          border: "1px dashed var(--border)",
          borderRadius: "16px",
          background: "var(--surface-muted)",
        }}
      >
        <span style={{ fontWeight: 700 }}>Source file</span>
        <input
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <span style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          Accepted formats: PDF, DOCX.
        </span>
      </label>
      {file ? (
        <div style={{ color: "var(--text-muted)" }}>
          Selected file: <strong style={{ color: "var(--text)" }}>{file.name}</strong>
        </div>
      ) : null}
      {error ? <p style={{ margin: 0, color: "#9b2c2c" }}>{error}</p> : null}
      <button
        type="submit"
        disabled={submitting}
        style={{
          height: "48px",
          width: "220px",
          border: 0,
          borderRadius: "12px",
          background: "var(--accent)",
          color: "#fff",
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        {submitting ? "Uploading…" : "Upload and analyze"}
      </button>
    </form>
  );
}
