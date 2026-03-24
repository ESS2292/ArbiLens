import { DocumentStatusResponse } from "@/lib/api/types";

export function isTerminalDocumentStatus(status: string): boolean {
  return status === "completed" || status === "failed";
}

export function getDocumentStatusTone(status: string): "neutral" | "warning" | "success" | "danger" {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "queued" || status === "uploaded") return "neutral";
  return "warning";
}

export function shouldPollStatus(status: DocumentStatusResponse | null): boolean {
  if (!status) return false;
  return !isTerminalDocumentStatus(status.document_status);
}
