import { expect, test } from "@playwright/test";

const now = "2026-03-24T12:00:00Z";

const organization = {
  id: "org-1",
  name: "Acme Legal",
  slug: "acme-legal",
};

const user = {
  id: "user-1",
  organization_id: "org-1",
  email: "reviewer@example.com",
  full_name: "Taylor Reviewer",
  role: "owner",
  is_active: true,
  created_at: now,
  updated_at: now,
};

test("sign in, upload a contract, and view completed analysis results", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "token-123",
        token_type: "bearer",
        user,
        organization,
      }),
    });
  });

  await page.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...user,
        organization,
      }),
    });
  });

  await page.route("**/api/v1/documents", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "doc-1",
        document_version_id: "ver-1",
        job_id: "job-1",
        job_status: "queued",
      }),
    });
  });

  await page.route("**/api/v1/documents/upload", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "doc-1",
        document_version_id: "ver-1",
        job_id: "job-1",
        job_status: "queued",
      }),
    });
  });

  await page.route("**/api/v1/documents/doc-1/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "doc-1",
        document_version_id: "ver-1",
        document_status: "completed",
        job_id: "job-1",
        job_status: "completed",
        current_stage: "completed",
        updated_at: now,
      }),
    });
  });

  await page.route("**/api/v1/documents/doc-1/summary", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "doc-1",
        document_version_id: "ver-1",
        analysis_job_id: "job-1",
        generated_from_status: "completed",
        overall_risk_score: 82,
        top_issues: [
          {
            risk_id: "risk-1",
            category: "liability",
            title: "Uncapped liability exposure",
            severity: "critical",
            score: 90,
            rationale: "The contract does not cap liability for indirect or consequential losses.",
            recommendation: "Add a liability cap tied to annual fees.",
            clause_id: "clause-1",
            citations: [
              {
                reference_type: "clause",
                clause_id: "clause-1",
                page_start: 4,
                page_end: 4,
              },
            ],
          },
        ],
        missing_protections: [],
        negotiation_priorities: [
          {
            priority_rank: 1,
            risk_id: "risk-1",
            title: "Uncapped liability exposure",
            category: "liability",
            recommendation: "Add a liability cap tied to annual fees.",
            severity: "critical",
          },
        ],
        clause_coverage_summary: [
          {
            clause_type: "limitation_of_liability",
            detected: true,
            clause_count: 1,
            clause_ids: ["clause-1"],
          },
        ],
        updated_at: now,
      }),
    });
  });

  await page.route("**/api/v1/documents/doc-1/clauses", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "clause-1",
          document_version_id: "ver-1",
          chunk_id: "chunk-1",
          clause_type: "limitation_of_liability",
          title: "Limitation of Liability",
          text: "Vendor shall have unlimited liability for all claims arising under this agreement.",
          normalized_text: "Vendor shall have unlimited liability for all claims arising under this agreement.",
          confidence: 0.98,
          source_method: "heuristic",
          page_start: 4,
          page_end: 4,
          start_char: 0,
          end_char: 90,
          created_at: now,
          updated_at: now,
        },
      ]),
    });
  });

  await page.route("**/api/v1/documents/doc-1/risks", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "risk-1",
          document_id: "doc-1",
          document_version_id: "ver-1",
          clause_id: "clause-1",
          analysis_job_id: "job-1",
          scope: "clause",
          severity: "critical",
          category: "liability",
          title: "Uncapped liability exposure",
          summary: "Liability exposure is uncapped.",
          score: 90,
          rationale: "The clause allows unlimited liability without a defined cap.",
          recommendation: "Add a liability cap tied to annual fees.",
          confidence: 0.95,
          citations: [
            {
              reference_type: "clause",
              clause_id: "clause-1",
              page_start: 4,
              page_end: 4,
            },
          ],
          deterministic_rule_code: "liability_uncapped",
          evidence_text: "Vendor shall have unlimited liability for all claims arising under this agreement.",
          created_at: now,
          updated_at: now,
        },
      ]),
    });
  });

  await page.route("**/api/v1/documents/doc-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "doc-1",
        filename: "msa.pdf",
        status: "completed",
        latest_version_number: 1,
        created_at: now,
        updated_at: now,
        current_job_status: "completed",
        current_stage: "completed",
        overall_risk_score: 82,
      }),
    });
  });

  await page.route("**/api/v1/billing", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        subscription_status: "free",
        stripe_customer_id: null,
        stripe_subscription_id: null,
        stripe_price_id: null,
        premium_access: false,
      }),
    });
  });

  await page.route("**/api/v1/reports/documents/doc-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.goto("/login");

  await page.getByLabel("Email").fill("reviewer@example.com");
  await page.getByLabel("Password").fill("supersecret123");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Contract review operations")).toBeVisible();

  await page.getByRole("link", { name: "Upload contract" }).click();
  await expect(page).toHaveURL(/\/documents\/upload$/);

  await page.setInputFiles('input[type="file"]', {
    name: "msa.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n% Mock contract\n", "utf8"),
  });
  await page.getByRole("button", { name: "Upload and analyze" }).click();

  await expect(page).toHaveURL(/\/documents\/doc-1$/);
  await expect(page.getByRole("heading", { name: "msa.pdf" })).toBeVisible();
  await expect(page.getByText("Overall risk score: 82")).toBeVisible();
  await expect(page.getByText("Uncapped liability exposure").first()).toBeVisible();
  await expect(page.getByText("Limitation of Liability", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Sources: clause (pages 4-4)")).toBeVisible();
});
