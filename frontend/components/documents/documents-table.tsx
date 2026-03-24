import Link from "next/link";

import { DocumentListItem } from "@/lib/api/types";
import { StatusBadge } from "@/components/shared/status-badge";

export function DocumentsTable({ documents }: { documents: DocumentListItem[] }) {
  return (
    <div className="panel" style={{ overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead style={{ background: "var(--surface-muted)", textAlign: "left" }}>
          <tr>
            {["Document", "Status", "Overall score", "Updated", "Open"].map((header) => (
              <th key={header} style={{ padding: "14px 18px", fontSize: "13px", color: "var(--text-muted)" }}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.id} style={{ borderTop: "1px solid var(--border)" }}>
              <td style={{ padding: "16px 18px" }}>
                <div style={{ fontWeight: 700 }}>{document.filename}</div>
                <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                  Version {document.latest_version_number}
                </div>
              </td>
              <td style={{ padding: "16px 18px" }}>
                <StatusBadge label={document.status} />
              </td>
              <td style={{ padding: "16px 18px", fontWeight: 700 }}>
                {document.overall_risk_score ?? "Pending"}
              </td>
              <td style={{ padding: "16px 18px", color: "var(--text-muted)" }}>
                {new Date(document.updated_at).toLocaleString()}
              </td>
              <td style={{ padding: "16px 18px" }}>
                <Link href={`/documents/${document.id}`} style={{ color: "var(--accent)", fontWeight: 700 }}>
                  View results
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
