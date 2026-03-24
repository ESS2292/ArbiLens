import { getDocumentStatusTone, isTerminalDocumentStatus, shouldPollStatus } from "./documents";

describe("document status helpers", () => {
  it("identifies terminal states", () => {
    expect(isTerminalDocumentStatus("completed")).toBe(true);
    expect(isTerminalDocumentStatus("failed")).toBe(true);
    expect(isTerminalDocumentStatus("parsing")).toBe(false);
  });

  it("returns the correct UI tone and polling behavior", () => {
    expect(getDocumentStatusTone("completed")).toBe("success");
    expect(getDocumentStatusTone("failed")).toBe("danger");
    expect(
      shouldPollStatus({
        document_id: "1",
        document_version_id: "1",
        document_status: "queued",
        job_id: "1",
        job_status: "queued",
        current_stage: "queued",
        updated_at: new Date().toISOString(),
      }),
    ).toBe(true);
  });
});
